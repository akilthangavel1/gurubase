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
import pytz
from datetime import time as dt_time
logger = logging.getLogger(__name__)
import time


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


def get_highest_daily_candle_with_date(ohlcv_daily_data):
    """
    Find the daily candle with the highest high price from the last 5 candles.
    
    Args:
        ohlcv_daily_data (pd.DataFrame): DataFrame containing daily OHLCV data
        
    Returns:
        str or None: Formatted "price (YYYY-MM-DD)" string, or None if data is insufficient
    """
    if not ohlcv_daily_data.empty and 'high_price' in ohlcv_daily_data.columns and 'close_price' in ohlcv_daily_data.columns and 'datetime' in ohlcv_daily_data.columns and len(ohlcv_daily_data) >= 5:
        # Restrict to last 5 daily candles
        top_5 = ohlcv_daily_data.head(5)
        highest_candle_idx = top_5['high_price'].idxmax()
        row = top_5.loc[highest_candle_idx]
        close_price = row['close_price']
        candle_date = row['datetime']
        # Format date as YYYY-MM-DD
        date_str = candle_date.strftime('%Y-%m-%d') if hasattr(candle_date, 'strftime') else str(candle_date)
        return f"{close_price} ({date_str})"
    
    return None

def calculate_daily_metrics(ohlcv_daily_data):
    """
    Calculate various metrics based on daily OHLCV data
    
    Args:
        ohlcv_daily_data (pd.DataFrame): DataFrame containing daily OHLCV data
        
    Returns:
        dict: Dictionary containing calculated daily metrics
    """
    daily_metrics = {}
    
    if not ohlcv_daily_data.empty and all(col in ohlcv_daily_data.columns for col in ['datetime', 'open_price', 'high_price', 'low_price', 'close_price']):
        # Daily highs and lows with dates
        daily_metrics.update({
            'day_top_latest_1_with_date': get_highest_daily_candle_with_date(ohlcv_daily_data),
            'day_top_previous_1_with_date': ohlcv_daily_data.iloc[1]['high_price'] if len(ohlcv_daily_data) > 1 else None,
            'day_top_previous_2_with_date': ohlcv_daily_data.iloc[2]['high_price'] if len(ohlcv_daily_data) > 2 else None,
            'day_bottom_latest_1_with_date': ohlcv_daily_data.iloc[0]['low_price'] if len(ohlcv_daily_data) > 0 else None,
            'day_bottom_previous_1_with_date': ohlcv_daily_data.iloc[1]['low_price'] if len(ohlcv_daily_data) > 1 else None,
            'day_bottom_previous_2_with_date': ohlcv_daily_data.iloc[2]['low_price'] if len(ohlcv_daily_data) > 2 else None,
            'day_close_latest_1_with_date': ohlcv_daily_data.iloc[0]['close_price'] if len(ohlcv_daily_data) > 0 else None,
            'day_close_previous_1_with_date': ohlcv_daily_data.iloc[1]['close_price'] if len(ohlcv_daily_data) > 1 else None,
            'day_close_previous_2_with_date': ohlcv_daily_data.iloc[2]['close_price'] if len(ohlcv_daily_data) > 2 else None,
        })
        
        # Additional daily stats
        daily_metrics.update({
            'daily_high_latest': ohlcv_daily_data.iloc[0]['high_price'] if len(ohlcv_daily_data) > 0 else None,
            'daily_low_latest': ohlcv_daily_data.iloc[0]['low_price'] if len(ohlcv_daily_data) > 0 else None,
            'daily_close_latest': ohlcv_daily_data.iloc[0]['close_price'] if len(ohlcv_daily_data) > 0 else None,
            'highest_top_out_of_last_5_daily_tops_with_date': ohlcv_daily_data.head(5)['high_price'].max() if len(ohlcv_daily_data) >= 5 else None,
            'highest_top_out_of_last_10_daily_tops_with_date': ohlcv_daily_data.head(10)['high_price'].max() if len(ohlcv_daily_data) >= 10 else None,
            'highest_top_out_of_last_20_daily_tops_with_date': ohlcv_daily_data.head(20)['high_price'].max() if len(ohlcv_daily_data) >= 20 else None,
            'highest_top_out_of_last_40_daily_tops_with_date': ohlcv_daily_data.head(40)['high_price'].max() if len(ohlcv_daily_data) >= 40 else None,
            'lowest_bottom_out_of_last_5_daily_bottoms_with_date': ohlcv_daily_data.head(5)['low_price'].min() if len(ohlcv_daily_data) >= 5 else None,
            'lowest_bottom_out_of_last_10_daily_bottoms_with_date': ohlcv_daily_data.head(10)['low_price'].min() if len(ohlcv_daily_data) >= 10 else None,
            'lowest_bottom_out_of_last_20_daily_bottoms_with_date': ohlcv_daily_data.head(20)['low_price'].min() if len(ohlcv_daily_data) >= 20 else None,
            'lowest_bottom_out_of_last_40_daily_bottoms_with_date': ohlcv_daily_data.head(40)['low_price'].min() if len(ohlcv_daily_data) >= 40 else None,
        })
        
        # Calculate daily ranges
        if len(ohlcv_daily_data) > 0:
            daily_metrics['daily_range_latest'] = ohlcv_daily_data.iloc[0]['high_price'] - ohlcv_daily_data.iloc[0]['low_price']
        if len(ohlcv_daily_data) > 1:
            daily_metrics['daily_range_previous_1'] = ohlcv_daily_data.iloc[1]['high_price'] - ohlcv_daily_data.iloc[1]['low_price']
        if len(ohlcv_daily_data) > 2:
            daily_metrics['daily_range_previous_2'] = ohlcv_daily_data.iloc[2]['high_price'] - ohlcv_daily_data.iloc[2]['low_price']
        
        # Calculate daily averages from the available data
        daily_metrics['daily_avg_high'] = ohlcv_daily_data['high_price'].mean()
        daily_metrics['daily_avg_low'] = ohlcv_daily_data['low_price'].mean()
        daily_metrics['daily_avg_close'] = ohlcv_daily_data['close_price'].mean()
        
        # Calculate average daily range
        daily_metrics['daily_avg_range'] = (ohlcv_daily_data['high_price'] - ohlcv_daily_data['low_price']).mean()
        
        # Calculate daily VWAP-like average
        daily_metrics['daily_avg_typical_price'] = ((ohlcv_daily_data['high_price'] + ohlcv_daily_data['low_price'] + ohlcv_daily_data['close_price'])/3).mean()
        
        # Add swing highs and lows if we have enough data
        if len(ohlcv_daily_data) >= 3:
            # Calculate swing highs and lows
            swing_highs, swing_lows = find_swing_highs_lows(ohlcv_daily_data['high_price'].tolist())
            
            # Add swing data to result
            if swing_highs:
                daily_metrics['day_previous_swing_top_1_with_date'] = swing_highs[0][1] if len(swing_highs) > 0 else None
                daily_metrics['day_previous_swing_top_2_with_date'] = swing_highs[1][1] if len(swing_highs) > 1 else None
                daily_metrics['day_previous_swing_top_3_with_date'] = swing_highs[2][1] if len(swing_highs) > 2 else None
            
            if swing_lows:
                daily_metrics['day_swing_bottom_1_with_date'] = swing_lows[0][1] if len(swing_lows) > 0 else None
                daily_metrics['day_previous_swing_bottom_2_with_date'] = swing_lows[1][1] if len(swing_lows) > 1 else None
                daily_metrics['day_previous_swing_bottom_3_with_date'] = swing_lows[2][1] if len(swing_lows) > 2 else None
    
    return daily_metrics

def _fetch_data_from_db(ticker_symbol, timeframe='1'):
    with connection.cursor() as cursor:
        table_name = f"{ticker_symbol}_future_daily_historical_data"
        query = f"""
            SELECT datetime, open_price, high_price, low_price, 
                   close_price, volume
            FROM "{table_name}"
            ORDER BY datetime DESC
            LIMIT 7  -- Fetch the last 7 records for daily calculations
        """
        cursor.execute(query)
        columns = [col[0] for col in cursor.description]  # Define columns from cursor description
        data = cursor.fetchall()
        ohlcv_daily_data = pd.DataFrame(data, columns=columns)
        
        # Calculate daily metrics
        daily_results = calculate_daily_metrics(ohlcv_daily_data)
    
    with connection.cursor() as cursor:
        table_name = f"{ticker_symbol}_future_historical_data"
        query = f"""
            SELECT datetime, open_price, high_price, low_price, 
                   close_price, volume
            FROM "{table_name}"
            ORDER BY datetime DESC
            LIMIT 700  -- Fetch the last 3 records for calculating ATP and swings
        """
        cursor.execute(query)
        columns = [col[0] for col in cursor.description]
        data = cursor.fetchall()
        ohlcv_data = pd.DataFrame(data, columns=columns)
        # Ensure the datetime column is timezone-aware, localize to UTC if naive, then convert to Asia/Kolkata
        if ohlcv_data['datetime'].dt.tz is None:
            ohlcv_data['datetime'] = ohlcv_data['datetime'].dt.tz_localize('UTC')
        ohlcv_data['datetime'] = ohlcv_data['datetime'].dt.tz_convert('Asia/Kolkata')

        # Preserve the original minute-level data before resampling
        ohlcv_minute_data = ohlcv_data.copy()

        # Sort chronologically so that the "first" and "last" aggregations behave as expected
        ohlcv_minute_data = ohlcv_minute_data.sort_values('datetime')

        # Align every timestamp to a 1-hour bin that starts at 9:15 AM each trading day
        offset = pd.Timedelta(hours=9, minutes=15)
        ohlcv_minute_data['interval'] = ((ohlcv_minute_data['datetime'] - offset).dt.floor('1h') + offset)

        # Group by the computed interval across all days
        ohlcv_one_hour_data = (
            ohlcv_minute_data.groupby('interval', as_index=False)
            .agg({
                'open_price': 'first',
                'high_price': 'max',
                'low_price': 'min',
                'close_price': 'last',
                'volume': 'sum'
            })
            .sort_values('interval', ascending=False)  # Keep newest interval first to match previous logic
        )

        # Rename the interval column back to datetime for downstream compatibility
        ohlcv_one_hour_data = ohlcv_one_hour_data.rename(columns={'interval': 'datetime'})
        
        # Create 30-minute data similar to 1-hour data
        offset_30min = pd.Timedelta(hours=9, minutes=15)
        ohlcv_minute_data['interval_30min'] = ((ohlcv_minute_data['datetime'] - offset_30min).dt.floor('30min') + offset_30min)

        # Group by 30-minute intervals
        ohlcv_30min_data = (
            ohlcv_minute_data.groupby('interval_30min', as_index=False)
            .agg({
                'open_price': 'first',
                'high_price': 'max', 
                'low_price': 'min',
                'close_price': 'last',
                'volume': 'sum'
            })
            .sort_values('interval_30min', ascending=False)
        )

        # Rename interval column to datetime
        ohlcv_30min_data = ohlcv_30min_data.rename(columns={'interval_30min': 'datetime'})
        
        # Add daily metrics info to log for debugging
        if not ohlcv_daily_data.empty:
            logger.debug(f"Daily data for {ticker_symbol}: {ohlcv_daily_data.head(3)}")
        
        result = {}
        
        # Add daily metrics to the result
        result.update(daily_results)

        result.update({
            'high_low_60_min_bar_9_am_10_am': f"H: {safe_get_value(ohlcv_one_hour_data, 6, 'high_price')}, L: {safe_get_value(ohlcv_one_hour_data, 6, 'low_price')}",
            'high_low_60_min_bar_10_am_11_am': f"H: {safe_get_value(ohlcv_one_hour_data, 5, 'high_price')}, L: {safe_get_value(ohlcv_one_hour_data, 5, 'low_price')}",
            'high_low_60_min_bar_11_am_12_pm': f"H: {safe_get_value(ohlcv_one_hour_data, 4, 'high_price')}, L: {safe_get_value(ohlcv_one_hour_data, 4, 'low_price')}",
            'high_low_60_min_bar_12_pm_1_pm': f"H: {safe_get_value(ohlcv_one_hour_data, 3, 'high_price')}, L: {safe_get_value(ohlcv_one_hour_data, 3, 'low_price')}",
            'high_low_60_min_bar_1_pm_2_pm': f"H: {safe_get_value(ohlcv_one_hour_data, 2, 'high_price')}, L: {safe_get_value(ohlcv_one_hour_data, 2, 'low_price')}",
            'high_low_60_min_bar_2_pm_3_pm': f"H: {safe_get_value(ohlcv_one_hour_data, 1, 'high_price')}, L: {safe_get_value(ohlcv_one_hour_data, 1, 'low_price')}",
            'high_low_60_min_bar_3_pm_4_pm': f"H: {safe_get_value(ohlcv_one_hour_data, 0, 'high_price')}, L: {safe_get_value(ohlcv_one_hour_data, 0, 'low_price')}",
            'current_day_30_mins_top_with_date_and_time_of_the_bar': get_current_day_30_mins_top_close_price(ohlcv_30min_data),
            'current_day_30_mins_bottom_with_date_and_time_of_the_bar': get_current_day_30_mins_bottom_close_price(ohlcv_30min_data),
            'last_5_tops_in_30_mins_with_date_and_time_of_the_bar': ohlcv_30min_data.head(5)['high_price'].max() if not ohlcv_30min_data.empty and 'high_price' in ohlcv_30min_data.columns and len(ohlcv_30min_data) >= 5 else None,
            'last_5_bottoms_in_30_mins_with_date_and_time_of_the_bar': ohlcv_30min_data.head(5)['low_price'].min() if not ohlcv_30min_data.empty and 'low_price' in ohlcv_30min_data.columns and len(ohlcv_30min_data) >= 5 else None,
            'highest_top_out_of_last_5_daily_tops_with_date': ohlcv_data.head(5)['high_price'].max() if not ohlcv_data.empty and 'high_price' in ohlcv_data.columns and len(ohlcv_data) >= 5 else None,
            'highest_top_out_of_last_10_daily_tops_with_date': ohlcv_data.head(10)['high_price'].max() if not ohlcv_data.empty and 'high_price' in ohlcv_data.columns and len(ohlcv_data) >= 10 else None,
            'highest_top_out_of_last_20_daily_tops_with_date': ohlcv_data.head(20)['high_price'].max() if not ohlcv_data.empty and 'high_price' in ohlcv_data.columns and len(ohlcv_data) >= 20 else None,
            'highest_top_out_of_last_40_daily_tops_with_date': ohlcv_data.head(40)['high_price'].max() if not ohlcv_data.empty and 'high_price' in ohlcv_data.columns and len(ohlcv_data) >= 40 else None,
            'day_bottom_latest_1_with_date': ohlcv_data.iloc[0]['low_price'] if not ohlcv_data.empty and 'low_price' in ohlcv_data.columns else None,
            'day_bottom_previous_1_with_date': ohlcv_data.iloc[1]['low_price'] if not ohlcv_data.empty and len(ohlcv_data) > 1 and 'low_price' in ohlcv_data.columns else None,
            'day_bottom_previous_2_with_date': ohlcv_data.iloc[2]['low_price'] if not ohlcv_data.empty and len(ohlcv_data) > 2 and 'low_price' in ohlcv_data.columns else None,
            'lowest_bottom_out_of_last_5_daily_bottoms_with_date': ohlcv_data.head(5)['low_price'].min() if not ohlcv_data.empty and 'low_price' in ohlcv_data.columns and len(ohlcv_data) >= 5 else None,
            'lowest_bottom_out_of_last_10_daily_bottoms_with_date': ohlcv_data.head(10)['low_price'].min() if not ohlcv_data.empty and 'low_price' in ohlcv_data.columns and len(ohlcv_data) >= 10 else None,
            'lowest_bottom_out_of_last_20_daily_bottoms_with_date': ohlcv_data.head(20)['low_price'].min() if not ohlcv_data.empty and 'low_price' in ohlcv_data.columns and len(ohlcv_data) >= 20 else None,
            'lowest_bottom_out_of_last_40_daily_bottoms_with_date': ohlcv_data.head(40)['low_price'].min() if not ohlcv_data.empty and 'low_price' in ohlcv_data.columns and len(ohlcv_data) >= 40 else None,
        })
        
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
        
        # Include ticker symbol for frontend reference
        result['ticker_symbol'] = ticker_symbol

        return result

# Remove ATP and swings calculation functions

# Add the safe_get_value function
def safe_get_value(df, index, column):
    """Safely get a value from a dataframe at a specific index and column."""
    try:
        if df is not None and not df.empty and len(df) > index and column in df.columns:
            return df.iloc[index][column]
        return None
    except Exception:
        return None

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

def get_current_day_30_mins_top_close_price(ohlcv_data):
    """
    Find the close price of the 30-minute candle with the highest high price from the last 5 candles.
    
    Args:
        ohlcv_data (pd.DataFrame): DataFrame containing OHLCV data
        
    Returns:
        str or None: Formatted "price @ date time" string, or None if data is insufficient
    """
    if 'high_price' in ohlcv_data.columns and 'close_price' in ohlcv_data.columns and len(ohlcv_data) >= 5:
        # Restrict to last 5 30-minute candles (already sorted newest first)
        top_5 = ohlcv_data.head(5)
        highest_candle_idx = top_5['high_price'].idxmax()
        row = top_5.loc[highest_candle_idx]
        close_price = row['close_price']
        bar_dt = row['datetime']
        # Format datetime as YYYY-MM-DD HH:MM (uses local tz already)
        bar_dt_str = bar_dt.strftime('%Y-%m-%d %H:%M') if hasattr(bar_dt, 'strftime') else str(bar_dt)
        return f"{close_price} ({bar_dt_str})"

    return None

# Add new function to get bottom 30-min candle close price with datetime
def get_current_day_30_mins_bottom_close_price(ohlcv_data):
    """
    Find the close price of the 30-minute candle with the lowest low price from the last 5 candles.

    Args:
        ohlcv_data (pd.DataFrame): DataFrame containing OHLCV data

    Returns:
        str or None: Formatted "price (YYYY-MM-DD HH:MM)" string, or None if data is insufficient
    """
    if 'low_price' in ohlcv_data.columns and 'close_price' in ohlcv_data.columns and len(ohlcv_data) >= 5:
        bottom_5 = ohlcv_data.head(5)
        lowest_candle_idx = bottom_5['low_price'].idxmin()
        row = bottom_5.loc[lowest_candle_idx]
        close_price = row['close_price']  # could also report low_price; keeping parallel to top impl
        bar_dt = row['datetime']
        bar_dt_str = bar_dt.strftime('%Y-%m-%d %H:%M') if hasattr(bar_dt, 'strftime') else str(bar_dt)
        return f"{close_price} ({bar_dt_str})"
    return None

async def generate_dynamic_stream(timeframe='1'):
    while True:
        try:
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
    # Valid options are '1' for 1-minute and '60' for 1-hour (custom 9:15 AM offset)
    timeframe = request.GET.get('timeframe', '1')
    
    # Validate timeframe
    if timeframe not in ['1', '60']:
        timeframe = '1'  # Default to 1-minute if invalid
    
    # Pass the timeframe to the stream generator
    response = StreamingHttpResponse(
        generate_dynamic_stream(timeframe),
        content_type='text/event-stream'
    )
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response
