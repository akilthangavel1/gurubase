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
            # For 10-minute timeframe, aligned to market hours starting at 9:15
            query = f"""
                WITH market_aligned_10min AS (
                    SELECT 
                        -- Special handling for the last 5-minute candle (3:25-3:30)
                        CASE
                            -- If time is between 3:25 PM and 3:30 PM, create a special interval
                            WHEN (EXTRACT(HOUR FROM datetime) = 15 AND EXTRACT(MINUTE FROM datetime) >= 25) 
                                THEN date_trunc('day', datetime) + INTERVAL '15 hours 25 minutes'
                            -- Otherwise use the standard 10-minute intervals from 9:15
                            ELSE
                                CASE
                                    -- Calculate the reference time (9:15 AM on the same day)
                                    WHEN EXTRACT(HOUR FROM datetime) < 9 OR (EXTRACT(HOUR FROM datetime) = 9 AND EXTRACT(MINUTE FROM datetime) < 15)
                                        THEN date_trunc('day', datetime - INTERVAL '1 day') + INTERVAL '9 hours 15 minutes'
                                    ELSE date_trunc('day', datetime) + INTERVAL '9 hours 15 minutes'
                                END +
                                -- Calculate how many 10-minute intervals have passed since 9:15
                                INTERVAL '10 minutes' * 
                                FLOOR(
                                    EXTRACT(EPOCH FROM (datetime - 
                                        CASE
                                            WHEN EXTRACT(HOUR FROM datetime) < 9 OR (EXTRACT(HOUR FROM datetime) = 9 AND EXTRACT(MINUTE FROM datetime) < 15)
                                                THEN date_trunc('day', datetime - INTERVAL '1 day') + INTERVAL '9 hours 15 minutes'
                                            ELSE date_trunc('day', datetime) + INTERVAL '9 hours 15 minutes'
                                        END
                                    )) / 600  -- 600 seconds = 10 minutes
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
                            -- If time is between 3:25 PM and 3:30 PM, create a special interval
                            WHEN (EXTRACT(HOUR FROM datetime) = 15 AND EXTRACT(MINUTE FROM datetime) >= 25) 
                                THEN date_trunc('day', datetime) + INTERVAL '15 hours 25 minutes'
                            -- Otherwise use the standard 10-minute intervals from 9:15
                            ELSE
                                CASE
                                    -- Calculate the reference time (9:15 AM on the same day)
                                    WHEN EXTRACT(HOUR FROM datetime) < 9 OR (EXTRACT(HOUR FROM datetime) = 9 AND EXTRACT(MINUTE FROM datetime) < 15)
                                        THEN date_trunc('day', datetime - INTERVAL '1 day') + INTERVAL '9 hours 15 minutes'
                                    ELSE date_trunc('day', datetime) + INTERVAL '9 hours 15 minutes'
                                END +
                                -- Calculate how many 10-minute intervals have passed since 9:15
                                INTERVAL '10 minutes' * 
                                FLOOR(
                                    EXTRACT(EPOCH FROM (datetime - 
                                        CASE
                                            WHEN EXTRACT(HOUR FROM datetime) < 9 OR (EXTRACT(HOUR FROM datetime) = 9 AND EXTRACT(MINUTE FROM datetime) < 15)
                                                THEN date_trunc('day', datetime - INTERVAL '1 day') + INTERVAL '9 hours 15 minutes'
                                            ELSE date_trunc('day', datetime) + INTERVAL '9 hours 15 minutes'
                                        END
                                    )) / 600
                                )
                        END
                        ORDER BY datetime
                        ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
                    )
                )
                SELECT DISTINCT interval_start as datetime, open_price, high_price, low_price, 
                       close_price, volume
                FROM market_aligned_10min
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
            # For 2-hour timeframe using a reference table of time slots with timezone adjustment
            # The data is in UTC (hours 3-4) but we want to interpret it as IST market hours (9:15-15:30)
            query = f"""
                WITH hour_slots AS (
                    -- Generate time slots for a trading day (UTC times)
                    -- We need 4 slots for 2-hour candles: 9:15-11:15, 11:15-13:15, 13:15-15:15, 15:15-15:30
                    -- UTC+5:30 -> UTC conversion: 9:15 IST = 3:45 UTC, 15:30 IST = 10:00 UTC
                    SELECT 0 as slot_id, '03:45'::time as slot_time, '09:15'::time as display_time  -- 9:15-11:15 IST = 3:45-5:45 UTC
                    UNION ALL
                    SELECT 1 as slot_id, '05:45'::time as slot_time, '11:15'::time as display_time  -- 11:15-13:15 IST = 5:45-7:45 UTC
                    UNION ALL
                    SELECT 2 as slot_id, '07:45'::time as slot_time, '13:15'::time as display_time  -- 13:15-15:15 IST = 7:45-9:45 UTC
                    UNION ALL
                    SELECT 3 as slot_id, '09:45'::time as slot_time, '15:15'::time as display_time  -- 15:15-15:30 IST = 9:45-10:00 UTC
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
                        td.day_date + hs.slot_time as interval_start,
                        td.day_date + hs.display_time as display_time,
                        hs.slot_id
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
                            -- Third 2-hour candle (13:15-15:15 IST)
                            (as_slot.slot_id = 2 AND
                             data.datetime >= as_slot.interval_start AND
                             data.datetime < as_slot.day_date + INTERVAL '9 hours 45 minutes')
                            OR
                            -- Special final 15-min candle (15:15-15:30 IST)
                            (as_slot.slot_id = 3 AND
                             data.datetime >= as_slot.interval_start AND
                             data.datetime <= as_slot.day_date + INTERVAL '10 hours')
                        )
                    WHERE
                        -- Only include data from trading hours (UTC times)
                        (EXTRACT(HOUR FROM datetime) >= 3 AND 
                         NOT (EXTRACT(HOUR FROM datetime) = 3 AND EXTRACT(MINUTE FROM datetime) < 45)) AND
                        (EXTRACT(HOUR FROM datetime) < 10 OR 
                         (EXTRACT(HOUR FROM datetime) = 10 AND EXTRACT(MINUTE FROM datetime) <= 0))
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
        ohlcv_data = pd.DataFrame(data, columns=columns)
        # print(ohlcv_data)
    
        if not ohlcv_data.empty:
            # Get latest candle data from DataFrame
            latest_data = ohlcv_data.iloc[0]
            previous_data = ohlcv_data.iloc[1] if len(ohlcv_data) > 1 else None
            last_3_data = ohlcv_data.iloc[:3]
            
            # Calculate ATP using DataFrame
            current_atp = calculate_atp_from_df(latest_data)
            previous_atp = calculate_atp_from_df(previous_data) if previous_data is not None else None
            last_3_atp = calculate_last_3_atp_from_df(last_3_data)
            
            # Log data for debugging instead of printing to console
            logger.debug(f"OHLCV data for {ticker_symbol}: {ohlcv_data.head().to_dict()}")
            
            # Calculate swings using DataFrame
            swings = calculate_swings_from_df(last_3_data)

            return {
                'ticker_symbol': ticker_symbol,
                'current_candle_open': round(float(latest_data['open_price']), 2) if pd.notna(latest_data['open_price']) else None,
                'current_candle_high': round(float(latest_data['high_price']), 2) if pd.notna(latest_data['high_price']) else None,
                'current_candle_low': round(float(latest_data['low_price']), 2) if pd.notna(latest_data['low_price']) else None,
                'current_candle_close': round(float(latest_data['close_price']), 2) if pd.notna(latest_data['close_price']) else None,
                'previous_candle_open': round(float(previous_data['open_price']), 2) if previous_data is not None and pd.notna(previous_data['open_price']) else None,
                'previous_candle_high': round(float(previous_data['high_price']), 2) if previous_data is not None and pd.notna(previous_data['high_price']) else None,
                'previous_candle_low': round(float(previous_data['low_price']), 2) if previous_data is not None and pd.notna(previous_data['low_price']) else None,
                'previous_candle_close': round(float(previous_data['close_price']), 2) if previous_data is not None and pd.notna(previous_data['close_price']) else None,
                'current_candle_atp': round(current_atp, 2) if current_atp is not None else None,
                'previous_candle_atp': round(previous_atp, 2) if previous_atp is not None else None,
                'last_3_candles_atp': round(last_3_atp, 2) if last_3_atp is not None else None,
                'prev_swing_high_1': round(swings['highs'][0], 2) if swings['highs'] and len(swings['highs']) > 0 and swings['highs'][0] is not None else None,
                'prev_swing_high_2': round(swings['highs'][1], 2) if swings['highs'] and len(swings['highs']) > 1 and swings['highs'][1] is not None else None,
                'prev_swing_high_3': round(swings['highs'][2], 2) if swings['highs'] and len(swings['highs']) > 2 and swings['highs'][2] is not None else None,
                'prev_swing_low_1': round(swings['lows'][0], 2) if swings['lows'] and len(swings['lows']) > 0 and swings['lows'][0] is not None else None,
                'prev_swing_low_2': round(swings['lows'][1], 2) if swings['lows'] and len(swings['lows']) > 1 and swings['lows'][1] is not None else None,
                'prev_swing_low_3': round(swings['lows'][2], 2) if swings['lows'] and len(swings['lows']) > 2 and swings['lows'][2] is not None else None,
                'bias': calculate_bias_from_df(latest_data, previous_data, swings)
            }
        return None

def calculate_atp_from_df(data):
    """Calculate Average Traded Price (ATP) from DataFrame row"""
    if data is None:
        return None
    return round((data['high_price'] + data['low_price'] + data['close_price']) / 3, 2)

def calculate_last_3_atp_from_df(data):
    """Calculate ATP for the last 3 candles using DataFrame"""
    if data is None or len(data) == 0:
        return None
    atps = [calculate_atp_from_df(data.iloc[i]) for i in range(len(data))]
    return round(sum(atps) / len(atps), 2)

def find_last_swing_highs(df, percentage_threshold=1.0, last_n=6):
    """
    Find last N swing highs in a DataFrame based on 'high_price'.
    
    Args:
        df (pd.DataFrame): DataFrame with 'datetime' and 'high_price' columns.
        percentage_threshold (float): Minimum percentage change to qualify as swing high.
        last_n (int): Number of swing highs to return.

    Returns:
        pd.DataFrame: DataFrame containing last N swing highs.
    """
    if len(df) < 3:
        return pd.DataFrame()
    
    swing_highs = []
    threshold = percentage_threshold / 100.0

    for i in range(1, len(df) - 1):
        prev_high = df.iloc[i - 1]['high_price']
        curr_high = df.iloc[i]['high_price']
        next_high = df.iloc[i + 1]['high_price']

        if (curr_high > prev_high and curr_high > next_high):
            if prev_high != 0 and next_high != 0:
                change_from_prev = (curr_high - prev_high) / prev_high
                change_to_next = (curr_high - next_high) / curr_high
                if change_from_prev >= threshold and change_to_next >= threshold:
                    swing_highs.append({
                        'datetime': df.iloc[i]['datetime'],
                        'high_price': curr_high,
                        'index': i
                    })

    # Create a DataFrame from swing highs
    swing_highs_df = pd.DataFrame(swing_highs)
    
    if swing_highs_df.empty:
        return swing_highs_df

    # Sort by datetime if needed
    swing_highs_df = swing_highs_df.sort_values(by='datetime', ascending=False).reset_index(drop=True)

    # Return only last N swings
    return swing_highs_df.head(last_n)

def find_last_swing_lows(df, percentage_threshold=1.0, last_n=6):
    """
    Find last N swing lows in a DataFrame based on 'low_price'.
    
    Args:
        df (pd.DataFrame): DataFrame with 'datetime' and 'low_price' columns.
        percentage_threshold (float): Minimum percentage change to qualify as swing low.
        last_n (int): Number of swing lows to return.

    Returns:
        pd.DataFrame: DataFrame containing last N swing lows.
    """
    if len(df) < 3:
        return pd.DataFrame()
    
    swing_lows = []
    threshold = percentage_threshold / 100.0

    for i in range(1, len(df) - 1):
        prev_low = df.iloc[i - 1]['low_price']
        curr_low = df.iloc[i]['low_price']
        next_low = df.iloc[i + 1]['low_price']

        if (curr_low < prev_low and curr_low < next_low):
            if prev_low != 0 and curr_low != 0:
                change_from_prev = (prev_low - curr_low) / prev_low
                change_to_next = (next_low - curr_low) / curr_low
                if change_from_prev >= threshold and change_to_next >= threshold:
                    swing_lows.append({
                        'datetime': df.iloc[i]['datetime'],
                        'low_price': curr_low,
                        'index': i
                    })

    # Create a DataFrame from swing lows
    swing_lows_df = pd.DataFrame(swing_lows)
    
    if swing_lows_df.empty:
        return swing_lows_df

    # Sort by datetime if needed
    swing_lows_df = swing_lows_df.sort_values(by='datetime', ascending=False).reset_index(drop=True)

    # Return only last N swings
    return swing_lows_df.head(last_n)

def calculate_swings_from_df(data):
    """Calculate swing highs and lows using the improved swing detection functions"""
    if data is None or len(data) == 0:
        return {'highs': [], 'lows': []}
    
    # Find swing highs and lows
    swing_highs_df = find_last_swing_highs(data, percentage_threshold=1.0, last_n=3)
    swing_lows_df = find_last_swing_lows(data, percentage_threshold=1.0, last_n=3)
    
    # Extract the values
    highs = swing_highs_df['high_price'].tolist() if not swing_highs_df.empty else []
    lows = swing_lows_df['low_price'].tolist() if not swing_lows_df.empty else []
    
    # If we don't have any swing points, fall back to simple max/min approach
    if not highs:
        highs = sorted(data['high_price'].tolist(), reverse=True)[:3]
    if not lows:
        lows = sorted(data['low_price'].tolist())[:3]
    
    return {'highs': highs, 'lows': lows}

def calculate_bias_from_df(latest_data, previous_data, swings):
    if latest_data is None or previous_data is None or not swings['highs'] or not swings['lows']:
        return 'NEUTRAL'
    current_price = latest_data['close_price']
    previous_close = previous_data['close_price']
    swing_high1 = swings['highs'][0] if len(swings['highs']) > 0 else None
    swing_low1 = swings['lows'][0] if len(swings['lows']) > 0 else None
    
    if swing_high1 is None or swing_low1 is None:
        return 'NEUTRAL'
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


    


# Keep the original functions for backward compatibility
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

    