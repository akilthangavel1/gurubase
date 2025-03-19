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
            # For 30-minute timeframe
            query = f"""
                WITH thirty_min_groups AS (
                    SELECT 
                        date_trunc('hour', datetime) + 
                        INTERVAL '30 min' * (date_part('minute', datetime)::integer / 30) AS interval_start,
                        FIRST_VALUE(open_price) OVER w AS open_price,
                        MAX(high_price) OVER w AS high_price,
                        MIN(low_price) OVER w AS low_price,
                        LAST_VALUE(close_price) OVER w AS close_price,
                        SUM(volume) OVER w AS volume
                    FROM "{table_name}"
                    WINDOW w AS (
                        PARTITION BY date_trunc('hour', datetime) + 
                        INTERVAL '30 min' * (date_part('minute', datetime)::integer / 30)
                        ORDER BY datetime
                        ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
                    )
                )
                SELECT DISTINCT interval_start as datetime, open_price, high_price, low_price, 
                       close_price, volume
                FROM thirty_min_groups
                ORDER BY interval_start DESC
                LIMIT 3  -- Fetch the last 3 records for calculating ATP and swings
            """
        elif timeframe == '60':
            # For 1-hour timeframe
            query = f"""
                WITH hourly_groups AS (
                    SELECT 
                        date_trunc('hour', datetime) AS interval_start,
                        FIRST_VALUE(open_price) OVER w AS open_price,
                        MAX(high_price) OVER w AS high_price,
                        MIN(low_price) OVER w AS low_price,
                        LAST_VALUE(close_price) OVER w AS close_price,
                        SUM(volume) OVER w AS volume
                    FROM "{table_name}"
                    WINDOW w AS (
                        PARTITION BY date_trunc('hour', datetime)
                        ORDER BY datetime
                        ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
                    )
                )
                SELECT DISTINCT interval_start as datetime, open_price, high_price, low_price, 
                       close_price, volume
                FROM hourly_groups
                ORDER BY interval_start DESC
                LIMIT 3  -- Fetch the last 3 records for calculating ATP and swings
            """
        elif timeframe == '240':
            # For 4-hour timeframe
            query = f"""
                WITH four_hour_groups AS (
                    SELECT 
                        date_trunc('day', datetime) + 
                        INTERVAL '4 hour' * (date_part('hour', datetime)::integer / 4) AS interval_start,
                        FIRST_VALUE(open_price) OVER w AS open_price,
                        MAX(high_price) OVER w AS high_price,
                        MIN(low_price) OVER w AS low_price,
                        LAST_VALUE(close_price) OVER w AS close_price,
                        SUM(volume) OVER w AS volume
                    FROM "{table_name}"
                    WINDOW w AS (
                        PARTITION BY date_trunc('day', datetime) + 
                        INTERVAL '4 hour' * (date_part('hour', datetime)::integer / 4)
                        ORDER BY datetime
                        ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
                    )
                )
                SELECT DISTINCT interval_start as datetime, open_price, high_price, low_price, 
                       close_price, volume
                FROM four_hour_groups
                ORDER BY interval_start DESC
                LIMIT 3  -- Fetch the last 3 records for calculating ATP and swings
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

def get_historical_data(ticker_symbol, timeframe='1'):
    try:
        with connection.cursor() as cursor:
            table_name = f"{ticker_symbol}_future_historical_data"
            
            if timeframe == '5':
                # For 5-minute timeframe, group the 1-minute data
                query = f"""
                    WITH five_min_groups AS (
                        SELECT 
                            date_trunc('hour', datetime) + 
                            INTERVAL '5 min' * (date_part('minute', datetime)::integer / 5) AS interval_start,
                            FIRST_VALUE(open_price) OVER w AS open_price,
                            MAX(high_price) OVER w AS high_price,
                            MIN(low_price) OVER w AS low_price,
                            LAST_VALUE(close_price) OVER w AS close_price,
                            SUM(volume) OVER w AS volume,
                            AVG((high_price + low_price + close_price)/3) OVER w AS atp
                        FROM "{table_name}"
                        WHERE datetime >= NOW() - INTERVAL '24 hours'
                        WINDOW w AS (
                            PARTITION BY date_trunc('hour', datetime) + 
                            INTERVAL '5 min' * (date_part('minute', datetime)::integer / 5)
                            ORDER BY datetime
                            ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
                        )
                    )
                    SELECT DISTINCT *
                    FROM five_min_groups
                    ORDER BY interval_start DESC
                """
            elif timeframe == '15':
                # For 15-minute timeframe, group the 1-minute data
                query = f"""
                    WITH fifteen_min_groups AS (
                        SELECT 
                            date_trunc('hour', datetime) + 
                            INTERVAL '15 min' * (date_part('minute', datetime)::integer / 15) AS interval_start,
                            FIRST_VALUE(open_price) OVER w AS open_price,
                            MAX(high_price) OVER w AS high_price,
                            MIN(low_price) OVER w AS low_price,
                            LAST_VALUE(close_price) OVER w AS close_price,
                            SUM(volume) OVER w AS volume,
                            AVG((high_price + low_price + close_price)/3) OVER w AS atp
                        FROM "{table_name}"
                        WHERE datetime >= NOW() - INTERVAL '24 hours'
                        WINDOW w AS (
                            PARTITION BY date_trunc('hour', datetime) + 
                            INTERVAL '15 min' * (date_part('minute', datetime)::integer / 15)
                            ORDER BY datetime
                            ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
                        )
                    )
                    SELECT DISTINCT *
                    FROM fifteen_min_groups
                    ORDER BY interval_start DESC
                """
            elif timeframe == '30':
                # For 30-minute timeframe, group the 1-minute data
                query = f"""
                    WITH thirty_min_groups AS (
                        SELECT 
                            date_trunc('hour', datetime) + 
                            INTERVAL '30 min' * (date_part('minute', datetime)::integer / 30) AS interval_start,
                            FIRST_VALUE(open_price) OVER w AS open_price,
                            MAX(high_price) OVER w AS high_price,
                            MIN(low_price) OVER w AS low_price,
                            LAST_VALUE(close_price) OVER w AS close_price,
                            SUM(volume) OVER w AS volume,
                            AVG((high_price + low_price + close_price)/3) OVER w AS atp
                        FROM "{table_name}"
                        WHERE datetime >= NOW() - INTERVAL '24 hours'
                        WINDOW w AS (
                            PARTITION BY date_trunc('hour', datetime) + 
                            INTERVAL '30 min' * (date_part('minute', datetime)::integer / 30)
                            ORDER BY datetime
                            ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
                        )
                    )
                    SELECT DISTINCT *
                    FROM thirty_min_groups
                    ORDER BY interval_start DESC
                """
            elif timeframe == '60':
                # For 1-hour timeframe, group the 1-minute data
                query = f"""
                    WITH hourly_groups AS (
                        SELECT 
                            date_trunc('hour', datetime) AS interval_start,
                            FIRST_VALUE(open_price) OVER w AS open_price,
                            MAX(high_price) OVER w AS high_price,
                            MIN(low_price) OVER w AS low_price,
                            LAST_VALUE(close_price) OVER w AS close_price,
                            SUM(volume) OVER w AS volume,
                            AVG((high_price + low_price + close_price)/3) OVER w AS atp
                        FROM "{table_name}"
                        WHERE datetime >= NOW() - INTERVAL '7 days'
                        WINDOW w AS (
                            PARTITION BY date_trunc('hour', datetime)
                            ORDER BY datetime
                            ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
                        )
                    )
                    SELECT DISTINCT *
                    FROM hourly_groups
                    ORDER BY interval_start DESC
                """
            elif timeframe == '240':
                # For 4-hour timeframe, group the 1-minute data
                query = f"""
                    WITH four_hour_groups AS (
                        SELECT 
                            date_trunc('day', datetime) + 
                            INTERVAL '4 hour' * (date_part('hour', datetime)::integer / 4) AS interval_start,
                            FIRST_VALUE(open_price) OVER w AS open_price,
                            MAX(high_price) OVER w AS high_price,
                            MIN(low_price) OVER w AS low_price,
                            LAST_VALUE(close_price) OVER w AS close_price,
                            SUM(volume) OVER w AS volume,
                            AVG((high_price + low_price + close_price)/3) OVER w AS atp
                        FROM "{table_name}"
                        WHERE datetime >= NOW() - INTERVAL '30 days'
                        WINDOW w AS (
                            PARTITION BY date_trunc('day', datetime) + 
                            INTERVAL '4 hour' * (date_part('hour', datetime)::integer / 4)
                            ORDER BY datetime
                            ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
                        )
                    )
                    SELECT DISTINCT *
                    FROM four_hour_groups
                    ORDER BY interval_start DESC
                """
            elif timeframe == '1440':
                # For 1-day timeframe (1440 minutes), group the 1-minute data
                query = f"""
                    WITH daily_groups AS (
                        SELECT 
                            date_trunc('day', datetime) AS interval_start,
                            FIRST_VALUE(open_price) OVER w AS open_price,
                            MAX(high_price) OVER w AS high_price,
                            MIN(low_price) OVER w AS low_price,
                            LAST_VALUE(close_price) OVER w AS close_price,
                            SUM(volume) OVER w AS volume,
                            AVG((high_price + low_price + close_price)/3) OVER w AS atp
                        FROM "{table_name}"
                        WHERE datetime >= NOW() - INTERVAL '90 days'
                        WINDOW w AS (
                            PARTITION BY date_trunc('day', datetime)
                            ORDER BY datetime
                            ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
                        )
                    )
                    SELECT DISTINCT *
                    FROM daily_groups
                    ORDER BY interval_start DESC
                """
            else:
                # For 1-minute timeframe, get raw data
                query = f"""
                    SELECT 
                        datetime,
                        open_price,
                        high_price,
                        low_price,
                        close_price,
                        volume,
                        (high_price + low_price + close_price)/3 as atp
                    FROM "{table_name}"
                    WHERE datetime >= NOW() - INTERVAL '24 hours'
                    ORDER BY datetime DESC
                """
            
            cursor.execute(query)
            data = cursor.fetchall()
            
            if not data:
                return None
                
            # Get the latest and previous candle data
            latest_data = data[0]
            previous_data = data[1] if len(data) > 1 else None
            
            # Calculate ATP (Average Trading Price) for last 3 candles
            last_3_data = data[:3]
            last_3_atp = sum([(d[2] + d[3] + d[4])/3 for d in last_3_data])/len(last_3_data) if len(last_3_data) > 0 else None
            
            # Calculate current and previous ATP
            current_atp = (latest_data[2] + latest_data[3] + latest_data[4])/3 if latest_data else None
            previous_atp = (previous_data[2] + previous_data[3] + previous_data[4])/3 if previous_data else None
            
            # Calculate swing points from last 20 candles
            last_20_candles = data[:20]
            highs, lows = find_swing_highs_lows([d[4] for d in last_20_candles])
            
            swings = {
                'highs': [h[1] for h in highs[:3]] + [None] * (3 - len(highs[:3])),
                'lows': [l[1] for l in lows[:3]] + [None] * (3 - len(lows[:3]))
            }
            
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
            
    except Exception as e:
        logger.error(f"Error fetching historical data for {ticker_symbol}: {str(e)}")
        return None

def find_swing_highs_lows(prices, percentage_threshold=1.0):
    """
    Calculate swing highs and lows based on a percentage threshold.
    
    Args:
        prices (list): List of price data (e.g., closing prices)
        percentage_threshold (float): Minimum percentage change to qualify as swing (default: 1.0%)
    
    Returns:
        tuple: (swing_highs, swing_lows) - Lists of tuples with (index, price)
    """
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

    