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
import time  # Import time module for sleep
logger = logging.getLogger(__name__)

# Create your views here.
def future_dynamic_data(request):
    return render(request, 'ddfuture/dynamic_data_future.html')

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
    """Helper function to fetch data from the database."""
    with connection.cursor() as cursor:
        table_name = f"{ticker_symbol}_future_historical_data"
        
        if timeframe == '5':
            # For 5-minute timeframe, use the same query from get_historical_data
            query = f"""
                WITH five_min_groups AS (
                    SELECT 
                        date_trunc('hour', datetime) + 
                        INTERVAL '5 min' * (date_part('minute', datetime)::integer / 5) AS interval_start,
                        FIRST_VALUE(open_price) OVER w AS open_price,
                        MAX(high_price) OVER w AS high_price,
                        MIN(low_price) OVER w AS low_price,
                        LAST_VALUE(close_price) OVER w AS close_price,
                        SUM(volume) OVER w AS volume
                    FROM "{table_name}"
                    WINDOW w AS (
                        PARTITION BY date_trunc('hour', datetime) + 
                        INTERVAL '5 min' * (date_part('minute', datetime)::integer / 5)
                        ORDER BY datetime
                        ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
                    )
                )
                SELECT DISTINCT interval_start as datetime, open_price, high_price, low_price, 
                       close_price, volume
                FROM five_min_groups
                ORDER BY interval_start DESC
                LIMIT 3  -- Fetch the last 3 records for calculating ATP and swings
            """
        elif timeframe == '10':
            # For 10-minute timeframe
            query = f"""
                WITH ten_min_groups AS (
                    SELECT 
                        date_trunc('hour', datetime) + 
                        INTERVAL '10 min' * (date_part('minute', datetime)::integer / 10) AS interval_start,
                        FIRST_VALUE(open_price) OVER w AS open_price,
                        MAX(high_price) OVER w AS high_price,
                        MIN(low_price) OVER w AS low_price,
                        LAST_VALUE(close_price) OVER w AS close_price,
                        SUM(volume) OVER w AS volume
                    FROM "{table_name}"
                    WINDOW w AS (
                        PARTITION BY date_trunc('hour', datetime) + 
                        INTERVAL '10 min' * (date_part('minute', datetime)::integer / 10)
                        ORDER BY datetime
                        ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
                    )
                )
                SELECT DISTINCT interval_start as datetime, open_price, high_price, low_price, 
                       close_price, volume
                FROM ten_min_groups
                ORDER BY interval_start DESC
                LIMIT 3  -- Fetch the last 3 records for calculating ATP and swings
            """
        elif timeframe == '15':
            # For 15-minute timeframe
            query = f"""
                WITH fifteen_min_groups AS (
                    SELECT 
                        date_trunc('hour', datetime) + 
                        INTERVAL '15 min' * (date_part('minute', datetime)::integer / 15) AS interval_start,
                        FIRST_VALUE(open_price) OVER w AS open_price,
                        MAX(high_price) OVER w AS high_price,
                        MIN(low_price) OVER w AS low_price,
                        LAST_VALUE(close_price) OVER w AS close_price,
                        SUM(volume) OVER w AS volume
                    FROM "{table_name}"
                    WINDOW w AS (
                        PARTITION BY date_trunc('hour', datetime) + 
                        INTERVAL '15 min' * (date_part('minute', datetime)::integer / 15)
                        ORDER BY datetime
                        ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
                    )
                )
                SELECT DISTINCT interval_start as datetime, open_price, high_price, low_price, 
                       close_price, volume
                FROM fifteen_min_groups
                ORDER BY interval_start DESC
                LIMIT 3  -- Fetch the last 3 records for calculating ATP and swings
            """
        elif timeframe == '30':
            # For 30-minute timeframe, aligned to market hours starting at 9:15
            query = f"""
                WITH market_aligned_30min AS (
                    SELECT 
                        -- Special handling for the last 15-minute candle (3:15-3:30)
                        CASE
                            -- If time is between 3:15 PM and 3:30 PM, create a special interval
                            WHEN (EXTRACT(HOUR FROM datetime) = 15 AND EXTRACT(MINUTE FROM datetime) >= 15) 
                                THEN date_trunc('day', datetime) + INTERVAL '15 hours 15 minutes'
                            -- Otherwise use the standard 30-minute intervals from 9:15
                            ELSE
                                CASE
                                    -- Calculate the reference time (9:15 AM on the same day)
                                    WHEN EXTRACT(HOUR FROM datetime) < 9 OR (EXTRACT(HOUR FROM datetime) = 9 AND EXTRACT(MINUTE FROM datetime) < 15)
                                        THEN date_trunc('day', datetime - INTERVAL '1 day') + INTERVAL '9 hours 15 minutes'
                                    ELSE date_trunc('day', datetime) + INTERVAL '9 hours 15 minutes'
                                END +
                                -- Calculate how many 30-minute intervals have passed since 9:15
                                INTERVAL '30 minutes' * 
                                FLOOR(
                                    EXTRACT(EPOCH FROM (datetime - 
                                        CASE
                                            WHEN EXTRACT(HOUR FROM datetime) < 9 OR (EXTRACT(HOUR FROM datetime) = 9 AND EXTRACT(MINUTE FROM datetime) < 15)
                                                THEN date_trunc('day', datetime - INTERVAL '1 day') + INTERVAL '9 hours 15 minutes'
                                            ELSE date_trunc('day', datetime) + INTERVAL '9 hours 15 minutes'
                                        END
                                    )) / 1800  -- 1800 seconds = 30 minutes
                                )
                        END AS interval_start,
                        FIRST_VALUE(open_price) OVER w AS open_price,
                        MAX(high_price) OVER w AS high_price,
                        MIN(low_price) OVER w AS low_price,
                        LAST_VALUE(close_price) OVER w AS close_price,
                        SUM(volume) OVER w AS volume
                    FROM "{table_name}"
                    WINDOW w AS (
                        PARTITION BY 
                        CASE
                            -- If time is between 3:15 PM and 3:30 PM, create a special interval
                            WHEN (EXTRACT(HOUR FROM datetime) = 15 AND EXTRACT(MINUTE FROM datetime) >= 15) 
                                THEN date_trunc('day', datetime) + INTERVAL '15 hours 15 minutes'
                            -- Otherwise use the standard 30-minute intervals from 9:15
                            ELSE
                                CASE
                                    -- Calculate the reference time (9:15 AM on the same day)
                                    WHEN EXTRACT(HOUR FROM datetime) < 9 OR (EXTRACT(HOUR FROM datetime) = 9 AND EXTRACT(MINUTE FROM datetime) < 15)
                                        THEN date_trunc('day', datetime - INTERVAL '1 day') + INTERVAL '9 hours 15 minutes'
                                    ELSE date_trunc('day', datetime) + INTERVAL '9 hours 15 minutes'
                                END +
                                -- Calculate how many 30-minute intervals have passed since 9:15
                                INTERVAL '30 minutes' * 
                                FLOOR(
                                    EXTRACT(EPOCH FROM (datetime - 
                                        CASE
                                            WHEN EXTRACT(HOUR FROM datetime) < 9 OR (EXTRACT(HOUR FROM datetime) = 9 AND EXTRACT(MINUTE FROM datetime) < 15)
                                                THEN date_trunc('day', datetime - INTERVAL '1 day') + INTERVAL '9 hours 15 minutes'
                                            ELSE date_trunc('day', datetime) + INTERVAL '9 hours 15 minutes'
                                        END
                                    )) / 1800
                                )
                        END
                        ORDER BY datetime
                        ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
                    )
                )
                SELECT DISTINCT interval_start as datetime, open_price, high_price, low_price, 
                       close_price, volume
                FROM market_aligned_30min
                ORDER BY interval_start DESC
                LIMIT 3  -- Fetch the last 3 records for calculating ATP and swings
            """
        elif timeframe == '45':
            # For 45-minute timeframe
            query = f"""
                WITH forty_five_min_groups AS (
                    SELECT 
                        date_trunc('hour', datetime) + 
                        INTERVAL '45 min' * (date_part('minute', datetime)::integer / 45) AS interval_start,
                        FIRST_VALUE(open_price) OVER w AS open_price,
                        MAX(high_price) OVER w AS high_price,
                        MIN(low_price) OVER w AS low_price,
                        LAST_VALUE(close_price) OVER w AS close_price,
                        SUM(volume) OVER w AS volume
                    FROM "{table_name}"
                    WINDOW w AS (
                        PARTITION BY date_trunc('hour', datetime) + 
                        INTERVAL '45 min' * (date_part('minute', datetime)::integer / 45)
                        ORDER BY datetime
                        ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
                    )
                )
                SELECT DISTINCT interval_start as datetime, open_price, high_price, low_price, 
                       close_price, volume
                FROM forty_five_min_groups
                ORDER BY interval_start DESC
                LIMIT 3  -- Fetch the last 3 records for calculating ATP and swings
            """
        elif timeframe == '60':
            # For 1-hour timeframe using a reference table of time slots with timezone adjustment
            # The data is in UTC (hours 3-4) but we want to interpret it as IST market hours (9:15-15:30)
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
        elif timeframe == '120':
            # For 2-hour timeframe
            query = f"""
                WITH hour_slots AS (
                    -- Generate time slots for a trading day (UTC times)
                    -- We need 3 slots for 2-hour candles: 9:15-11:15, 11:15-13:15, 13:15-15:30
                    -- UTC+5:30 -> UTC conversion: 9:15 IST = 3:45 UTC, 15:30 IST = 10:00 UTC
                    VALUES
                        (0, '03:45'::time, '09:15'::time),  -- 9:15-11:15 IST = 3:45-5:45 UTC
                        (1, '05:45'::time, '11:15'::time),  -- 11:15-13:15 IST = 5:45-7:45 UTC
                        (2, '07:45'::time, '13:15'::time)   -- 13:15-15:30 IST = 7:45-10:00 UTC
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
                    -- Cross join to create all possible 2-hour slots for all trading days
                    SELECT 
                        td.day_date,
                        td.day_date + hs.column2 as interval_start,
                        td.day_date + hs.column3 as display_time,
                        hs.column1 as slot_id
                    FROM trading_days td
                    CROSS JOIN hour_slots hs
                ),
                hour_candles AS (
                    -- Match data points to their corresponding 2-hour slot (in UTC)
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
                            -- First 2-hour candle (9:15-11:15 IST)
                            (as_slot.slot_id = 0 AND 
                             data.datetime >= as_slot.interval_start AND 
                             data.datetime < as_slot.day_date + INTERVAL '5 hours 45 minutes')
                            OR
                            -- Second 2-hour candle (11:15-13:15 IST)
                            (as_slot.slot_id = 1 AND
                             data.datetime >= as_slot.interval_start AND 
                             data.datetime < as_slot.day_date + INTERVAL '7 hours 45 minutes')
                            OR
                            -- Third 2-hour candle including last period (13:15-15:30 IST)
                            (as_slot.slot_id = 2 AND
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
                    -- Aggregate the data within each 2-hour slot
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
        elif timeframe == '240':
            # For 4-hour timeframe using a reference table of time slots with timezone adjustment
            # The data is in UTC (hours 3-4) but we want to interpret it as IST market hours (9:15-15:30)
            query = f"""
                WITH hour_slots AS (
                    -- Generate time slots for a trading day (UTC times)
                    -- We only need 2 slots for 4-hour candles: 9:15-13:15, 13:15-15:30
                    -- UTC+5:30 -> UTC conversion: 9:15 IST = 3:45 UTC, 15:30 IST = 10:00 UTC
                    VALUES
                        (0, '03:45'::time, '09:15'::time),  -- 9:15-13:15 IST = 3:45-7:45 UTC
                        (1, '07:45'::time, '13:15'::time)   -- 13:15-15:30 IST = 7:45-10:00 UTC
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
                    -- Cross join to create all possible 4-hour slots for all trading days
                    SELECT 
                        td.day_date,
                        td.day_date + hs.column2 as interval_start,
                        td.day_date + hs.column3 as display_time,
                        hs.column1 as slot_id
                    FROM trading_days td
                    CROSS JOIN hour_slots hs
                ),
                hour_candles AS (
                    -- Match data points to their corresponding 4-hour slot (in UTC)
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
                            -- First 4-hour candle (9:15-13:15 IST)
                            (as_slot.slot_id = 0 AND 
                             data.datetime >= as_slot.interval_start AND 
                             data.datetime < as_slot.day_date + INTERVAL '7 hours 45 minutes')
                            OR
                            -- Second 4-hour candle including last period (13:15-15:30 IST)
                            (as_slot.slot_id = 1 AND
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
                    -- Aggregate the data within each 4-hour slot
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
        elif timeframe == '1440':
            # For 1-day timeframe (24 hours = 1440 minutes)
            query = f"""
                WITH daily_groups AS (
                    SELECT 
                        date_trunc('day', datetime) AS interval_start,
                        FIRST_VALUE(open_price) OVER w AS open_price,
                        MAX(high_price) OVER w AS high_price,
                        MIN(low_price) OVER w AS low_price,
                        LAST_VALUE(close_price) OVER w AS close_price,
                        SUM(volume) OVER w AS volume
                    FROM "{table_name}"
                    WINDOW w AS (
                        PARTITION BY date_trunc('day', datetime)
                        ORDER BY datetime
                        ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
                    )
                )
                SELECT DISTINCT interval_start as datetime, open_price, high_price, low_price, 
                       close_price, volume
                FROM daily_groups
                ORDER BY interval_start DESC
                LIMIT 3  -- Fetch the last 3 records for calculating ATP and swings
            """
        else:
            # For 1-minute timeframe, use the original query
            query = f"""
                SELECT datetime, open_price, high_price, low_price, 
                       close_price, volume
                FROM "{table_name}"
                ORDER BY datetime DESC
                LIMIT 3  -- Fetch the last 3 records for calculating ATP and swings
            """
        
        cursor.execute(query)
        columns = [col[0] for col in cursor.description]
        data = cursor.fetchall()
        if data:
            # Process data to calculate required fields
            latest_data = data[0]
            previous_data = data[1] if len(data) > 1 else None
            last_3_data = data[:3]

            # Calculate ATP and swings
            current_atp = calculate_atp(latest_data)
            previous_atp = calculate_atp(previous_data) if previous_data else None
            last_3_atp = calculate_last_3_atp(last_3_data)

            # Calculate swings
            swings = calculate_swings(last_3_data)

            return {
                'ticker_symbol': ticker_symbol,
                'current_candle_open': round(latest_data[1], 2) if latest_data[1] is not None else None,
                'current_candle_high': round(latest_data[2], 2) if latest_data[2] is not None else None,
                'current_candle_low': round(latest_data[3], 2) if latest_data[3] is not None else None,
                'current_candle_close': round(latest_data[4], 2) if latest_data[4] is not None else None,
                'previous_candle_open': round(previous_data[1], 2) if previous_data and previous_data[1] is not None else None,
                'previous_candle_high': round(previous_data[2], 2) if previous_data and previous_data[2] is not None else None,
                'previous_candle_low': round(previous_data[3], 2) if previous_data and previous_data[3] is not None else None,
                'previous_candle_close': round(previous_data[4], 2) if previous_data and previous_data[4] is not None else None,
                'current_candle_atp': round(current_atp, 2) if current_atp is not None else None,
                'previous_candle_atp': round(previous_atp, 2) if previous_atp is not None else None,
                'last_3_candles_atp': round(last_3_atp, 2) if last_3_atp is not None else None,
                'prev_swing_high_1': round(swings['highs'][0], 2) if swings['highs'][0] is not None else None,
                'prev_swing_high_2': round(swings['highs'][1], 2) if swings['highs'][1] is not None else None,
                'prev_swing_high_3': round(swings['highs'][2], 2) if swings['highs'][2] is not None else None,
                'prev_swing_low_1': round(swings['lows'][0], 2) if swings['lows'][0] is not None else None,
                'prev_swing_low_2': round(swings['lows'][1], 2) if swings['lows'][1] is not None else None,
                'prev_swing_low_3': round(swings['lows'][2], 2) if swings['lows'][2] is not None else None,
                'bias': calculate_bias(latest_data, previous_data, swings)
            }
        return None

def calculate_atp(data):
    """Calculate Average Traded Price (ATP)"""
    if not data:
        return None
    return round((data[2] + data[3] + data[4]) / 3, 2)

def calculate_last_3_atp(data):
    """Calculate ATP for the last 3 candles"""
    if not data:
        return None
    return round(sum(calculate_atp(d) for d in data) / len(data), 2)

def calculate_swings(data):
    """Calculate swing highs and lows"""
    highs = sorted([d[2] for d in data], reverse=True)[:3]
    lows = sorted([d[3] for d in data])[:3]
    return {'highs': highs, 'lows': lows}

def calculate_bias(latest_data, previous_data, swings):
    """Determine market bias"""
    if not latest_data or not previous_data:
        return 'NEUTRAL'
    current_price = latest_data[4]
    previous_close = previous_data[4]
    swing_high1 = swings['highs'][0]
    swing_low1 = swings['lows'][0]

    if current_price > previous_close and current_price > swing_high1:
        return 'BULLISH'
    elif current_price < previous_close and current_price < swing_low1:
        return 'BEARISH'
    else:
        return 'NEUTRAL'

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

def sse_dynamic_data(request):
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

# Example usage with sample data
if __name__ == "__main__":
    # Sample price data (e.g., daily closing prices)
    price_data = [100, 102, 105, 103, 101, 99, 97, 100, 102, 101, 98]
    
    # Set percentage threshold (e.g., 1% change)
    threshold = 2.0  # 2% change required
    
    # Calculate swings
    highs, lows = find_swing_highs_lows(price_data, threshold)
    
    # Print results
    print("Swing Highs (index, price):")
    for high in highs:
        print(f"Index: {high[0]}, Price: {high[1]}")
    
    print("\nSwing Lows (index, price):")
    for low in lows:
        print(f"Index: {low[0]}, Price: {low[1]}")
    
    # Optional: Visualize the data
    import matplotlib.pyplot as plt
    
    plt.plot(price_data, label='Price', marker='o')
    for high in highs:
        plt.plot(high[0], high[1], 'ro', label='Swing High' if high == highs[0] else "")
    for low in lows:
        plt.plot(low[0], low[1], 'go', label='Swing Low' if low == lows[0] else "")
    plt.legend()
    plt.title(f"Swing Highs and Lows ({threshold}% threshold)")
    plt.xlabel("Time")
    plt.ylabel("Price")
    plt.grid(True)
    plt.show()

    