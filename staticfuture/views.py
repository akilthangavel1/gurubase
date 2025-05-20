from django.shortcuts import render
import asyncio
import json
from django.http import StreamingHttpResponse
from asgiref.sync import sync_to_async
import pandas as pd
from django.db import connection
import logging
from dashboard.models import TickerBase
from django.core.serializers.json import DjangoJSONEncoder
from django.utils.http import urlencode
import pytz  # Add pytz for timezone support
logger = logging.getLogger(__name__)
import time

# Create your views here.
def static_future_data(request):
    return render(request, 'staticfuture/staticindex.html')

async def fetch_latest_data(ticker_symbol, timeframe='1'):
    """Fetch the latest data for a given ticker symbol."""
    try:
        # Use sync_to_async to wrap the database operation
        data = await sync_to_async(_fetch_data_from_db)(ticker_symbol, timeframe)
        return data
    except Exception as e:
        logger.error(f"Error fetching data for {ticker_symbol}: {str(e)}")
        return None


def _fetch_data_from_db(ticker_symbol, timeframe='1'):
    print("#########################")
    with connection.cursor() as cursor:
        table_name = f"{ticker_symbol}_future_historical_data"
        # Always use the 1-minute timeframe query
        query = f"""
            SELECT datetime, open_price, high_price, low_price, 
                   close_price, volume
            FROM "{table_name}"
            ORDER BY datetime DESC
            LIMIT 700 
        """
        cursor.execute(query)
        columns = [col[0] for col in cursor.description]
        data = cursor.fetchall()
        ohlcv_data = pd.DataFrame(data, columns=columns)


        query = f"""
                WITH hour_slots AS (
                    -- Generate all possible hour slots for a trading day (UTC times)
                    -- UTC+5:30 -> UTC conversion: 9:15 IST = 3:45 UTC, 15:30 IST = 10:00 UTC
                    SELECT generate_series(0, 6) as slot_id,
                           '03:45'::time + (generate_series(0, 6) || ' hour')::interval as slot_time,
                           '09:15'::time + (generate_series(0, 6) || ' hour')::interval as display_time
                ),
                trading_days AS (
                    -- Get distinct days from the data
                    SELECT DISTINCT date_trunc('day', datetime) as day_date
                    FROM "{table_name}"
                    WHERE
                        -- Only include data from trading hours (UTC times)
                        (EXTRACT(HOUR FROM datetime) >= 3 AND 
                         NOT (EXTRACT(HOUR FROM datetime) = 3 AND EXTRACT(MINUTE FROM datetime) < 45)) AND
                        (EXTRACT(HOUR FROM datetime) < 10 OR 
                         (EXTRACT(HOUR FROM datetime) = 10 AND EXTRACT(MINUTE FROM datetime) <= 0))
                ),
                all_slots AS (
                    -- Cross join to create all possible hour slots for all trading days
                    SELECT 
                        td.day_date,
                        td.day_date + hs.slot_time as interval_start,
                        td.day_date + hs.display_time as display_time,
                        hs.slot_id
                    FROM trading_days td
                    CROSS JOIN hour_slots hs
                ),
                hour_candles AS (
                    -- Match data points to their corresponding hour slot (in UTC)
                    SELECT 
                        as_slot.display_time as display_interval,
                        as_slot.interval_start,
                        data.datetime,
                        data.open_price,
                        data.high_price,
                        data.low_price,
                        data.close_price,
                        data.volume
                    FROM "{table_name}" data
                    JOIN all_slots as_slot
                        ON date_trunc('day', data.datetime) = as_slot.day_date
                        -- Match data to candle based on time (UTC)
                        AND (
                            -- Regular 1-hour candles
                            (as_slot.slot_id < 6 AND 
                             data.datetime >= as_slot.interval_start AND 
                             data.datetime < as_slot.interval_start + INTERVAL '1 hour')
                            OR
                            -- Special case for the last candle (15:15-15:30 IST = 9:45-10:00 UTC)
                            (as_slot.slot_id = 6 AND
                             data.datetime >= as_slot.interval_start AND
                             data.datetime <= as_slot.day_date + INTERVAL '10 hours')
                        )
                    WHERE
                        -- Only include data from trading hours (UTC times)
                        (EXTRACT(HOUR FROM data.datetime) >= 3 AND 
                         NOT (EXTRACT(HOUR FROM data.datetime) = 3 AND EXTRACT(MINUTE FROM data.datetime) < 45)) AND
                        (EXTRACT(HOUR FROM data.datetime) < 10 OR 
                         (EXTRACT(HOUR FROM data.datetime) = 10 AND EXTRACT(MINUTE FROM data.datetime) <= 0))
                ),
                aggregated_candles AS (
                    -- Aggregate the data within each hour slot
                    SELECT 
                        display_interval,
                        FIRST_VALUE(open_price) OVER (PARTITION BY display_interval ORDER BY datetime) AS open_price,
                        MAX(high_price) OVER (PARTITION BY display_interval) AS high_price,
                        MIN(low_price) OVER (PARTITION BY display_interval) AS low_price,
                        LAST_VALUE(close_price) OVER (PARTITION BY display_interval ORDER BY datetime ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) AS close_price,
                        SUM(volume) OVER (PARTITION BY display_interval) AS volume
                    FROM hour_candles
                ),
                final_candles AS (
                    -- Remove duplicates
                    SELECT DISTINCT
                        display_interval,
                        open_price,
                        high_price,
                        low_price,
                        close_price,
                        volume
                    FROM aggregated_candles
                )
                
                SELECT display_interval as datetime, open_price, high_price, low_price, close_price, volume
                FROM final_candles
                ORDER BY display_interval DESC
                LIMIT 3 -- Fetch the last 3 records for calculating ATP and swings
            """
        cursor.execute(query)
        columns = [col[0] for col in cursor.description]
        data_one_hour = cursor.fetchall()
        ohlcv_data_one_hour = pd.DataFrame(data_one_hour, columns=columns)
        print(ohlcv_data_one_hour.head())
        if not ohlcv_data.empty and 'datetime' in ohlcv_data.columns:
            ohlcv_data['datetime'] = pd.to_datetime(ohlcv_data['datetime'])
            # If your DB stores UTC, localize to UTC first, then convert to IST
            if ohlcv_data['datetime'].dt.tz is None or ohlcv_data['datetime'].dt.tz is pytz.UTC:
                ohlcv_data['datetime'] = ohlcv_data['datetime'].dt.tz_localize('UTC').dt.tz_convert('Asia/Kolkata')
            else:
                ohlcv_data['datetime'] = ohlcv_data['datetime'].dt.tz_convert('Asia/Kolkata')
        # print(ohlcv_data.head())
        # for i, r in ohlcv_data.iterrows():
        #     print(r.datetime)
        # time.sleep(100)
        result = {
            'ticker_symbol': ticker_symbol,
            # Use ohlcv_data for calculations
            # 'high_low_60_min_bar_9_am_10_am': f"H: {ohlcv_data[(ohlcv_data['datetime'].dt.date == ohlcv_data['datetime'].dt.date.max()) & ((ohlcv_data['datetime'].dt.hour == 9) & (ohlcv_data['datetime'].dt.minute >= 15)) | ((ohlcv_data['datetime'].dt.hour == 10) & (ohlcv_data['datetime'].dt.minute < 15))]['high_price'].max() if 'high_price' in ohlcv_data.columns and hasattr(ohlcv_data['datetime'], 'dt') else 'N/A'}, L: {ohlcv_data[(ohlcv_data['datetime'].dt.date == ohlcv_data['datetime'].dt.date.max()) & ((ohlcv_data['datetime'].dt.hour == 9) & (ohlcv_data['datetime'].dt.minute >= 15)) | ((ohlcv_data['datetime'].dt.hour == 10) & (ohlcv_data['datetime'].dt.minute < 15))]['low_price'].min() if 'low_price' in ohlcv_data.columns and hasattr(ohlcv_data['datetime'], 'dt') else 'N/A'}",
            # 'high_low_60_min_bar_10_am_11_am': f"H: {ohlcv_data[(ohlcv_data['datetime'].dt.date == ohlcv_data['datetime'].dt.date.max()) & ((ohlcv_data['datetime'].dt.hour == 10) & (ohlcv_data['datetime'].dt.minute >= 15)) | ((ohlcv_data['datetime'].dt.hour == 11) & (ohlcv_data['datetime'].dt.minute < 15))]['high_price'].max() if 'high_price' in ohlcv_data.columns and hasattr(ohlcv_data['datetime'], 'dt') else 'N/A'}, L: {ohlcv_data[(ohlcv_data['datetime'].dt.date == ohlcv_data['datetime'].dt.date.max()) & ((ohlcv_data['datetime'].dt.hour == 10) & (ohlcv_data['datetime'].dt.minute >= 15)) | ((ohlcv_data['datetime'].dt.hour == 11) & (ohlcv_data['datetime'].dt.minute < 15))]['low_price'].min() if 'low_price' in ohlcv_data.columns and hasattr(ohlcv_data['datetime'], 'dt') else 'N/A'}",
            # 'high_low_60_min_bar_11_am_12_pm': f"H: {ohlcv_data[(ohlcv_data['datetime'].dt.date == ohlcv_data['datetime'].dt.date.max()) & ((ohlcv_data['datetime'].dt.hour == 11) & (ohlcv_data['datetime'].dt.minute >= 15)) | ((ohlcv_data['datetime'].dt.hour == 12) & (ohlcv_data['datetime'].dt.minute < 15))]['high_price'].max() if 'high_price' in ohlcv_data.columns and hasattr(ohlcv_data['datetime'], 'dt') else 'N/A'}, L: {ohlcv_data[(ohlcv_data['datetime'].dt.date == ohlcv_data['datetime'].dt.date.max()) & ((ohlcv_data['datetime'].dt.hour == 11) & (ohlcv_data['datetime'].dt.minute >= 15)) | ((ohlcv_data['datetime'].dt.hour == 12) & (ohlcv_data['datetime'].dt.minute < 15))]['low_price'].min() if 'low_price' in ohlcv_data.columns and hasattr(ohlcv_data['datetime'], 'dt') else 'N/A'}",
            # 'high_low_60_min_bar_12_pm_1_pm': f"H: {ohlcv_data[(ohlcv_data['datetime'].dt.date == ohlcv_data['datetime'].dt.date.max()) & ((ohlcv_data['datetime'].dt.hour == 12) & (ohlcv_data['datetime'].dt.minute >= 15)) | ((ohlcv_data['datetime'].dt.hour == 13) & (ohlcv_data['datetime'].dt.minute < 15))]['high_price'].max() if 'high_price' in ohlcv_data.columns and hasattr(ohlcv_data['datetime'], 'dt') else 'N/A'}, L: {ohlcv_data[(ohlcv_data['datetime'].dt.date == ohlcv_data['datetime'].dt.date.max()) & ((ohlcv_data['datetime'].dt.hour == 12) & (ohlcv_data['datetime'].dt.minute >= 15)) | ((ohlcv_data['datetime'].dt.hour == 13) & (ohlcv_data['datetime'].dt.minute < 15))]['low_price'].min() if 'low_price' in ohlcv_data.columns and hasattr(ohlcv_data['datetime'], 'dt') else 'N/A'}",
            # 'high_low_60_min_bar_1_pm_2_pm': f"H: {ohlcv_data[(ohlcv_data['datetime'].dt.date == ohlcv_data['datetime'].dt.date.max()) & ((ohlcv_data['datetime'].dt.hour == 13) & (ohlcv_data['datetime'].dt.minute >= 15)) | ((ohlcv_data['datetime'].dt.hour == 14) & (ohlcv_data['datetime'].dt.minute < 15))]['high_price'].max() if 'high_price' in ohlcv_data.columns and hasattr(ohlcv_data['datetime'], 'dt') else 'N/A'}, L: {ohlcv_data[(ohlcv_data['datetime'].dt.date == ohlcv_data['datetime'].dt.date.max()) & ((ohlcv_data['datetime'].dt.hour == 13) & (ohlcv_data['datetime'].dt.minute >= 15)) | ((ohlcv_data['datetime'].dt.hour == 14) & (ohlcv_data['datetime'].dt.minute < 15))]['low_price'].min() if 'low_price' in ohlcv_data.columns and hasattr(ohlcv_data['datetime'], 'dt') else 'N/A'}",
            # 'high_low_60_min_bar_2_pm_3_pm': f"H: {ohlcv_data[(ohlcv_data['datetime'].dt.date == ohlcv_data['datetime'].dt.date.max()) & ((ohlcv_data['datetime'].dt.hour == 14) & (ohlcv_data['datetime'].dt.minute >= 15)) | ((ohlcv_data['datetime'].dt.hour == 15) & (ohlcv_data['datetime'].dt.minute < 15))]['high_price'].max() if 'high_price' in ohlcv_data.columns and hasattr(ohlcv_data['datetime'], 'dt') else 'N/A'}, L: {ohlcv_data[(ohlcv_data['datetime'].dt.date == ohlcv_data['datetime'].dt.date.max()) & ((ohlcv_data['datetime'].dt.hour == 14) & (ohlcv_data['datetime'].dt.minute >= 15)) | ((ohlcv_data['datetime'].dt.hour == 15) & (ohlcv_data['datetime'].dt.minute < 15))]['low_price'].min() if 'low_price' in ohlcv_data.columns and hasattr(ohlcv_data['datetime'], 'dt') else 'N/A'}",
            # 'high_low_60_min_bar_3_pm_4_pm': f"H: {ohlcv_data[(ohlcv_data['datetime'].dt.date == ohlcv_data['datetime'].dt.date.max()) & ((ohlcv_data['datetime'].dt.hour == 15) & (ohlcv_data['datetime'].dt.minute >= 15) & (ohlcv_data['datetime'].dt.minute <= 30))]['high_price'].max() if 'high_price' in ohlcv_data.columns and hasattr(ohlcv_data['datetime'], 'dt') else 'N/A'}, L: {ohlcv_data[(ohlcv_data['datetime'].dt.date == ohlcv_data['datetime'].dt.date.max()) & ((ohlcv_data['datetime'].dt.hour == 15) & (ohlcv_data['datetime'].dt.minute >= 15) & (ohlcv_data['datetime'].dt.minute <= 30))]['low_price'].min() if 'low_price' in ohlcv_data.columns and hasattr(ohlcv_data['datetime'], 'dt') else 'N/A'}",
            'current_day_30_mins_top_with_date_and_time_of_the_bar': ohlcv_data.iloc[0]['high_price'] if 'high_price' in ohlcv_data.columns else None,
            'current_day_30_mins_bottom_with_date_and_time_of_the_bar': ohlcv_data.iloc[0]['low_price'] if 'low_price' in ohlcv_data.columns else None,
            'last_5_tops_in_30_mins_with_date_and_time_of_the_bar': ohlcv_data.head(5)['high_price'].max() if 'high_price' in ohlcv_data.columns else None,
            'last_5_bottoms_in_30_mins_with_date_and_time_of_the_bar': ohlcv_data.head(5)['low_price'].min() if 'low_price' in ohlcv_data.columns else None,
            'day_top_latest_1_with_date': ohlcv_data.iloc[0]['high_price'] if 'high_price' in ohlcv_data.columns else None,
            'day_top_previous_1_with_date': ohlcv_data.iloc[1]['high_price'] if len(ohlcv_data) > 1 and 'high_price' in ohlcv_data.columns else None,
            'day_top_previous_2_with_date': ohlcv_data.iloc[2]['high_price'] if len(ohlcv_data) > 2 and 'high_price' in ohlcv_data.columns else None,
            'highest_top_out_of_last_5_daily_tops_with_date': ohlcv_data.head(5)['high_price'].max() if 'high_price' in ohlcv_data.columns else None,
            'highest_top_out_of_last_10_daily_tops_with_date': ohlcv_data.head(10)['high_price'].max() if 'high_price' in ohlcv_data.columns else None,
            'highest_top_out_of_last_20_daily_tops_with_date': ohlcv_data.head(20)['high_price'].max() if 'high_price' in ohlcv_data.columns else None,
            'highest_top_out_of_last_40_daily_tops_with_date': ohlcv_data.head(40)['high_price'].max() if 'high_price' in ohlcv_data.columns else None,
            'day_bottom_latest_1_with_date': ohlcv_data.iloc[0]['low_price'] if 'low_price' in ohlcv_data.columns else None,
            'day_bottom_previous_1_with_date': ohlcv_data.iloc[1]['low_price'] if len(ohlcv_data) > 1 and 'low_price' in ohlcv_data.columns else None,
            'day_bottom_previous_2_with_date': ohlcv_data.iloc[2]['low_price'] if len(ohlcv_data) > 2 and 'low_price' in ohlcv_data.columns else None,
            'lowest_bottom_out_of_last_5_daily_bottoms_with_date': ohlcv_data.head(5)['low_price'].min() if 'low_price' in ohlcv_data.columns else None,
            'lowest_bottom_out_of_last_10_daily_bottoms_with_date': ohlcv_data.head(10)['low_price'].min() if 'low_price' in ohlcv_data.columns else None,
            'lowest_bottom_out_of_last_20_daily_bottoms_with_date': ohlcv_data.head(20)['low_price'].min() if 'low_price' in ohlcv_data.columns else None,
            'lowest_bottom_out_of_last_40_daily_bottoms_with_date': ohlcv_data.head(40)['low_price'].min() if 'low_price' in ohlcv_data.columns else None,
        }
        
        # Add swing highs and lows if we have enough data
        if len(ohlcv_data) >= 3 and 'high_price' in ohlcv_data.columns and 'low_price' in ohlcv_data.columns:
            # Calculate swing highs and lows
            swing_highs, swing_lows = find_swing_highs_lows(ohlcv_data['high_price'].tolist())
            
            # Add swing data to result
            if swing_highs:
                result['day_previous_swing_top_1_with_date'] = swing_highs[0][1] if len(swing_highs) > 0 else None
                result['day_previous_swing_top_2_with_date'] = swing_highs[1][1] if len(swing_highs) > 1 else None
                result['day_previous_swing_top_3_with_date'] = swing_highs[2][1] if len(swing_highs) > 2 else None
            
            if swing_lows:
                result['day_swing_bottom_1_with_date'] = swing_lows[0][1] if len(swing_lows) > 0 else None
                result['day_previous_swing_bottom_2_with_date'] = swing_lows[1][1] if len(swing_lows) > 1 else None
                result['day_previous_swing_bottom_3_with_date'] = swing_lows[2][1] if len(swing_lows) > 2 else None
        
        # Add weekly and monthly data
        if 'close_price' in ohlcv_data.columns and 'high_price' in ohlcv_data.columns and 'low_price' in ohlcv_data.columns:
            # Weekly calculations
            result.update({
                'previous_friday_high': ohlcv_data.iloc[0]['high_price'] if 'high_price' in ohlcv_data.columns else None,
                'previous_friday_low': ohlcv_data.iloc[0]['low_price'] if 'low_price' in ohlcv_data.columns else None,
                'previous_friday_close': ohlcv_data.iloc[0]['close_price'] if 'close_price' in ohlcv_data.columns else None,
                'expiry_week_open': ohlcv_data.iloc[-1]['open_price'] if 'open_price' in ohlcv_data.columns and len(ohlcv_data) > 0 else None,
                'expiry_week_high': ohlcv_data['high_price'].max() if 'high_price' in ohlcv_data.columns else None,
                'expiry_week_low': ohlcv_data['low_price'].min() if 'low_price' in ohlcv_data.columns else None,
                'expiry_week_vwap': ((ohlcv_data['high_price'] + ohlcv_data['low_price'] + ohlcv_data['close_price'])/3).mean() if all(col in ohlcv_data.columns for col in ['high_price', 'low_price', 'close_price']) else None,
                'expiry_week_close': ohlcv_data.iloc[0]['close_price'] if 'close_price' in ohlcv_data.columns else None,
                'rollover_week_open': ohlcv_data.iloc[-1]['open_price'] if 'open_price' in ohlcv_data.columns and len(ohlcv_data) > 0 else None,
                'rollover_week_high': ohlcv_data['high_price'].max() if 'high_price' in ohlcv_data.columns else None,
                'rollover_week_low': ohlcv_data['low_price'].min() if 'low_price' in ohlcv_data.columns else None,
                'roll_over_week_vwap': ((ohlcv_data['high_price'] + ohlcv_data['low_price'] + ohlcv_data['close_price'])/3).mean() if all(col in ohlcv_data.columns for col in ['high_price', 'low_price', 'close_price']) else None,
                'rollover_week_close': ohlcv_data.iloc[0]['close_price'] if 'close_price' in ohlcv_data.columns else None,

                # Weekly tops and bottoms
                'week_top_latest_1_with_date': ohlcv_data.iloc[0]['high_price'] if 'high_price' in ohlcv_data.columns else None,
                'week_top_previous_1_with_date': ohlcv_data.iloc[1]['high_price'] if len(ohlcv_data) > 1 and 'high_price' in ohlcv_data.columns else None,
                'week_top_previous_2_with_date': ohlcv_data.iloc[2]['high_price'] if len(ohlcv_data) > 2 and 'high_price' in ohlcv_data.columns else None,
                'highest_top_out_of_last_4_weekly_tops_with_date': ohlcv_data.head(4)['high_price'].max() if 'high_price' in ohlcv_data.columns else None,
                'highest_top_out_of_last_8_weekly_tops_with_date': ohlcv_data.head(8)['high_price'].max() if 'high_price' in ohlcv_data.columns else None,
                'highest_top_out_of_last_12_weekly_tops_with_date': ohlcv_data.head(12)['high_price'].max() if 'high_price' in ohlcv_data.columns else None,
                'highest_top_out_of_last_16_weekly_tops_with_date': ohlcv_data.head(16)['high_price'].max() if 'high_price' in ohlcv_data.columns else None,
                'week_bottom_latest_1_with_date': ohlcv_data.iloc[0]['low_price'] if 'low_price' in ohlcv_data.columns else None,
                'week_bottom_previous_1_with_date': ohlcv_data.iloc[1]['low_price'] if len(ohlcv_data) > 1 and 'low_price' in ohlcv_data.columns else None,
                'week_bottom_previous_2_with_date': ohlcv_data.iloc[2]['low_price'] if len(ohlcv_data) > 2 and 'low_price' in ohlcv_data.columns else None,
                'lowest_bottom_out_of_last_4_weekly_bottoms_with_date': ohlcv_data.head(4)['low_price'].min() if 'low_price' in ohlcv_data.columns else None,
                'lowest_bottom_out_of_last_8_weekly_bottoms_with_date': ohlcv_data.head(8)['low_price'].min() if 'low_price' in ohlcv_data.columns else None,
                'lowest_bottom_out_of_last_12_weekly_bottoms_with_date': ohlcv_data.head(12)['low_price'].min() if 'low_price' in ohlcv_data.columns else None,
                'lowest_bottom_out_of_last_16_weekly_bottoms_with_date': ohlcv_data.head(16)['low_price'].min() if 'low_price' in ohlcv_data.columns else None,

                # Monthly tops and bottoms
                'month_top_1_with_date': ohlcv_data.iloc[0]['high_price'] if 'high_price' in ohlcv_data.columns else None,
                'month_top_2_with_date': ohlcv_data.iloc[1]['high_price'] if len(ohlcv_data) > 1 and 'high_price' in ohlcv_data.columns else None,
                'month_top_3_with_date': ohlcv_data.iloc[2]['high_price'] if len(ohlcv_data) > 2 and 'high_price' in ohlcv_data.columns else None,
                'highest_top_out_of_last_2_monthly_tops_with_date': ohlcv_data.head(2)['high_price'].max() if 'high_price' in ohlcv_data.columns else None,
                'highest_top_out_of_last_4_monthly_tops_with_date': ohlcv_data.head(4)['high_price'].max() if 'high_price' in ohlcv_data.columns else None,
                'highest_top_out_of_last_6_monthly_tops_with_date': ohlcv_data.head(6)['high_price'].max() if 'high_price' in ohlcv_data.columns else None,
                'month_bottom_1_with_date': ohlcv_data.iloc[0]['low_price'] if 'low_price' in ohlcv_data.columns else None,
                'month_bottom_2_with_date': ohlcv_data.iloc[1]['low_price'] if len(ohlcv_data) > 1 and 'low_price' in ohlcv_data.columns else None,
                'month_bottom_3_with_date': ohlcv_data.iloc[2]['low_price'] if len(ohlcv_data) > 2 and 'low_price' in ohlcv_data.columns else None,
                'lowest_bottom_out_of_last_2_monthly_bottoms_with_date': ohlcv_data.head(2)['low_price'].min() if 'low_price' in ohlcv_data.columns else None,
                'lowest_bottom_out_of_last_4_monthly_bottoms_with_date': ohlcv_data.head(4)['low_price'].min() if 'low_price' in ohlcv_data.columns else None,
                'lowest_bottom_out_of_last_6_monthly_bottoms_with_date': ohlcv_data.head(6)['low_price'].min() if 'low_price' in ohlcv_data.columns else None,
                
                # Add the following fields that were in the original code
                'expiry_week_high_low_volume_bar': ohlcv_data.loc[ohlcv_data['volume'].idxmax()]['high_price'] if 'volume' in ohlcv_data.columns and 'high_price' in ohlcv_data.columns else None,
                'roll_over_week_high_low_volume_bar': ohlcv_data.loc[ohlcv_data['volume'].idxmax()]['high_price'] if 'volume' in ohlcv_data.columns and 'high_price' in ohlcv_data.columns else None,
            })
        
        return result

# Remove ATP and swings calculation functions

# Add the find_swing_highs_lows function
def find_swing_highs_lows(prices, percentage_threshold=1.0):
    
    if len(prices) < 3:
        return [], []  # Need at least 3 points to determine swings
    
    swing_highs = []
    swing_lows = []
    threshold = percentage_threshold / 100.0
    
    for i in range(1, len(prices) - 1):
        prev_price = prices[i - 1]
        curr_price = prices[i]
        next_price = prices[i + 1]
        
        # Check for swing high
        if (curr_price > prev_price and curr_price > next_price):
            # Verify if the change exceeds the percentage threshold
            if (prev_price != 0 and next_price != 0):  # Avoid division by zero
                change_from_prev = (curr_price - prev_price) / prev_price
                change_to_next = (curr_price - next_price) / curr_price
                if change_from_prev >= threshold and change_to_next >= threshold:
                    swing_highs.append((i, curr_price))
        
        # Check for swing low
        if (curr_price < prev_price and curr_price < next_price):
            # Verify if the change exceeds the percentage threshold
            if (prev_price != 0 and curr_price != 0):  # Avoid division by zero
                change_from_prev = (prev_price - curr_price) / prev_price
                change_to_next = (next_price - curr_price) / curr_price
                if change_from_prev >= threshold and change_to_next >= threshold:
                    swing_lows.append((i, curr_price))
    
    return swing_highs, swing_lows

async def generate_dynamic_stream(timeframe='1'):
    while True:
        try:
            # Get all tickers
            tickers = await sync_to_async(list)(TickerBase.objects.all())
            formatted_data = []

            for ticker in tickers:
                # Fetch data based on the timeframe
                data = await fetch_latest_data(ticker.ticker_symbol, timeframe)
                if data:
                    formatted_data.append(data)

            if formatted_data:
                yield f"data: {json.dumps(formatted_data, cls=DjangoJSONEncoder)}\n\n"
            else:
                yield f"data: {json.dumps({'message': 'No data available'}, cls=DjangoJSONEncoder)}\n\n"

            # Log the timeframe being used
            logger.debug(f"Streaming data with timeframe: {timeframe}")
            await asyncio.sleep(1)  # Update every second

        except Exception as e:
            logger.error(f"Error in generate_dynamic_stream: {str(e)}")
            yield f"data: {json.dumps({'error': str(e)}, cls=DjangoJSONEncoder)}\n\n"
            await asyncio.sleep(1)

def sse_static_future_data(request):
    """SSE endpoint for real-time dynamic data updates with timeframe support"""
    # Get the timeframe from the query parameters, default to '1' if not provided
    timeframe = request.GET.get('timeframe', '1')

    # Pass the timeframe to the stream generator
    response = StreamingHttpResponse(
        generate_dynamic_stream(timeframe),
        content_type='text/event-stream'
    )
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response
