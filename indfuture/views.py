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
import pandas_ta as ta


logger = logging.getLogger(__name__)

def calculate_custom_macd(prices, fast_period=12, slow_period=26, signal_period=9):
    """
    Custom MACD calculation function
    
    Args:
        prices: Series of closing prices
        fast_period: Fast EMA period (default: 12)
        slow_period: Slow EMA period (default: 26)
        signal_period: Signal line EMA period (default: 9)
    
    Returns:
        tuple: (macd_line, signal_line, histogram)
    """
    # Calculate EMAs
    ema_fast = prices.ewm(span=fast_period).mean()
    ema_slow = prices.ewm(span=slow_period).mean()
    
    # MACD Line = Fast EMA - Slow EMA
    macd_line = ema_fast - ema_slow
    
    # Signal Line = EMA of MACD Line
    signal_line = macd_line.ewm(span=signal_period).mean()
    
    # Histogram = MACD Line - Signal Line
    histogram = macd_line - signal_line
    
    return macd_line, signal_line, histogram


def indicator_future(request):
    logger.info("Rendering indicator_future template")
    return render(request, 'indfuture/indicator_future.html')


def future_dynamic_data(request):
    return render(request, 'ddfuture/dynamic_data_future.html')


def calculate_indicators(data, daily_data=None, ema_length=10, sma_length=10, hma_length=10, macd_fast=12, macd_slow=26, macd_signal=9, supertrend_length=14, supertrend_multiplier=3, keltner_ema_length=20, keltner_atr_length=14, keltner_multiplier=2):
   
    # Convert main data to DataFrame
    df = pd.DataFrame(data, columns=['datetime', 'open', 'high', 'low', 'close', 'volume'])
    df['datetime'] = pd.to_datetime(df['datetime'])

    # Sort the DataFrame by 'datetime' in ascending order
    df = df.sort_values(by='datetime', ascending=True)

    # Find the highest indicator length to determine minimum required data points
    max_length = max(ema_length, sma_length, hma_length, macd_slow, supertrend_length, keltner_ema_length, keltner_atr_length)
    required_rows = max_length * 2  # Double the highest value for better accuracy
    
    # If we have more rows than required, slice the dataframe to keep only the needed rows
    if len(df) > required_rows:
        df = df.iloc[-required_rows:]

    df['ema'] = ta.ema(df['close'], length=ema_length)

    # Calculate SMA
    df['sma'] = ta.sma(df['close'], length=sma_length)
    

    df['hma'] = ta.hma(df['close'], length=hma_length)


    macd_line, signal_line, histogram = calculate_custom_macd(
        df['close'], 
        fast_period=macd_fast, 
        slow_period=macd_slow, 
        signal_period=macd_signal
    )
    df['macd'] = macd_line
    df['signal_line'] = signal_line

    # Calculate Supertrend
    supertrend = ta.supertrend(df['high'], df['low'], df['close'], length=supertrend_length, multiplier=supertrend_multiplier)
    df['supertrend'] = supertrend['SUPERT_'+str(supertrend_length)+"_"+str(supertrend_multiplier)]

    # Calculate Awesome Oscillator
    df['ao'] = ta.ao(df['high'], df['low'])

    # Calculate Keltner Channels with user-specified parameters
    keltner = ta.kc(df['high'], df['low'], df['close'], length=keltner_ema_length, scalar=keltner_multiplier, mamode='ema', atr_length=keltner_atr_length)
    kc_upper_key = f'KCUe_{keltner_ema_length}_{keltner_multiplier}'
    kc_middle_key = f'KCBe_{keltner_ema_length}_{keltner_multiplier}'
    kc_lower_key = f'KCLe_{keltner_ema_length}_{keltner_multiplier}'
    
    if kc_upper_key in keltner.columns:    
        df['keltner_upper'] = keltner[kc_upper_key]
    else:
        logger.warning(f"Keltner column {kc_upper_key} not found. Using default fallback.")
        df['keltner_upper'] = keltner[keltner.columns[0]]  # Fallback to first column
        
    if kc_middle_key in keltner.columns:
        df['keltner_middle'] = keltner[kc_middle_key]
    else:
        logger.warning(f"Keltner column {kc_middle_key} not found. Using default fallback.")
        df['keltner_middle'] = keltner[keltner.columns[1]]  # Fallback to second column
        
    if kc_lower_key in keltner.columns:
        df['keltner_lower'] = keltner[kc_lower_key]
    else:
        logger.warning(f"Keltner column {kc_lower_key} not found. Using default fallback.")
        df['keltner_lower'] = keltner[keltner.columns[2]]  # Fallback to third column

    # Calculate pivot points from daily data if provided
    if daily_data and len(daily_data) > 0:
        # Convert daily data to DataFrame
        daily_df = pd.DataFrame(daily_data, columns=['datetime', 'open', 'high', 'low', 'close', 'volume'])
        daily_df['datetime'] = pd.to_datetime(daily_df['datetime'])
        
        # Sort the DataFrame by 'datetime' in ascending order
        daily_df = daily_df.sort_values(by='datetime', ascending=True)
        
        # Use the latest daily candle for pivot calculations
        latest_daily = daily_df.iloc[-1]
        
        # Calculate Classic Pivot Points from daily data
        pivot = (latest_daily['high'] + latest_daily['low'] + latest_daily['close']) / 3
        r1 = 2 * pivot - latest_daily['low']
        s1 = 2 * pivot - latest_daily['high']
        r2 = pivot + (latest_daily['high'] - latest_daily['low'])
        s2 = pivot - (latest_daily['high'] - latest_daily['low'])
        r3 = latest_daily['high'] + 2 * (pivot - latest_daily['low'])
        s3 = latest_daily['low'] - 2 * (latest_daily['high'] - pivot)
        
        # Calculate Camarilla Pivot Points from daily data
        camarilla_r1 = latest_daily['close'] + (latest_daily['high'] - latest_daily['low']) * 1.1 / 12
        camarilla_r2 = latest_daily['close'] + (latest_daily['high'] - latest_daily['low']) * 1.1 / 6
        camarilla_r3 = latest_daily['close'] + (latest_daily['high'] - latest_daily['low']) * 1.1 / 4
        camarilla_r4 = latest_daily['close'] + (latest_daily['high'] - latest_daily['low']) * 1.1 / 2
        camarilla_s1 = latest_daily['close'] - (latest_daily['high'] - latest_daily['low']) * 1.1 / 12
        camarilla_s2 = latest_daily['close'] - (latest_daily['high'] - latest_daily['low']) * 1.1 / 6
        camarilla_s3 = latest_daily['close'] - (latest_daily['high'] - latest_daily['low']) * 1.1 / 4
        camarilla_s4 = latest_daily['close'] - (latest_daily['high'] - latest_daily['low']) * 1.1 / 2
        
        # Add these values to all rows in the main DataFrame
        df['pivot'] = pivot
        df['r1'] = r1
        df['s1'] = s1
        df['r2'] = r2
        df['s2'] = s2
        df['r3'] = r3
        df['s3'] = s3
        df['camarilla_r1'] = camarilla_r1
        df['camarilla_r2'] = camarilla_r2
        df['camarilla_r3'] = camarilla_r3
        df['camarilla_r4'] = camarilla_r4
        df['camarilla_s1'] = camarilla_s1
        df['camarilla_s2'] = camarilla_s2
        df['camarilla_s3'] = camarilla_s3
        df['camarilla_s4'] = camarilla_s4
    else:
        # If no daily data provided, calculate from the input data as fallback
        logger.warning("No daily data provided for pivot calculations. Using current timeframe data as fallback.")
        
        # Calculate Classic Pivot Points from current timeframe
        df['pivot'] = (df['high'] + df['low'] + df['close']) / 3
        df['r1'] = 2 * df['pivot'] - df['low']
        df['s1'] = 2 * df['pivot'] - df['high']
        df['r2'] = df['pivot'] + (df['high'] - df['low'])
        df['s2'] = df['pivot'] - (df['high'] - df['low'])
        df['r3'] = df['high'] + 2 * (df['pivot'] - df['low'])
        df['s3'] = df['low'] - 2 * (df['high'] - df['pivot'])

        # Calculate Camarilla Pivot Points from current timeframe
        df['camarilla_r1'] = df['close'] + (df['high'] - df['low']) * 1.1 / 12
        df['camarilla_r2'] = df['close'] + (df['high'] - df['low']) * 1.1 / 6
        df['camarilla_r3'] = df['close'] + (df['high'] - df['low']) * 1.1 / 4
        df['camarilla_r4'] = df['close'] + (df['high'] - df['low']) * 1.1 / 2
        df['camarilla_s1'] = df['close'] - (df['high'] - df['low']) * 1.1 / 12
        df['camarilla_s2'] = df['close'] - (df['high'] - df['low']) * 1.1 / 6
        df['camarilla_s3'] = df['close'] - (df['high'] - df['low']) * 1.1 / 4
        df['camarilla_s4'] = df['close'] - (df['high'] - df['low']) * 1.1 / 2

    # Return the latest values
    latest_data = df.iloc[-1]
    return {
        'ema': latest_data['ema'],
        'sma': latest_data['sma'],
        'hma': latest_data['hma'],
        'macd': latest_data['macd'],
        'signal_line': latest_data['signal_line'],
        'supertrend': latest_data['supertrend'],
        'ao': latest_data['ao'],
        'keltner_upper': latest_data['keltner_upper'],
        'keltner_middle': latest_data['keltner_middle'],
        'keltner_lower': latest_data['keltner_lower'],
        'pivot': latest_data['pivot'],
        'r1': latest_data['r1'],
        's1': latest_data['s1'],
        'r2': latest_data['r2'],
        's2': latest_data['s2'],
        'r3': latest_data['r3'],
        's3': latest_data['s3'],
        'camarilla_r1': latest_data['camarilla_r1'],
        'camarilla_r2': latest_data['camarilla_r2'],
        'camarilla_r3': latest_data['camarilla_r3'],
        'camarilla_r4': latest_data['camarilla_r4'],
        'camarilla_s1': latest_data['camarilla_s1'],
        'camarilla_s2': latest_data['camarilla_s2'],
        'camarilla_s3': latest_data['camarilla_s3'],
        'camarilla_s4': latest_data['camarilla_s4']
    }

def stream_indicator_data(request):
    """SSE endpoint for real-time dynamic data updates with timeframe and indicator support"""
    # Get the timeframe and indicator parameters from the query parameters
    timeframe = request.GET.get('timeframe', '1')
    ema = request.GET.get('ema', '10')
    ema = '10' if ema == '0' else ema  # Default EMA to 10 if 0
    sma = request.GET.get('sma', '10')
    sma = '10' if sma == '0' else sma 
    hma = request.GET.get('hma', '10')
    hma = '10' if hma == '0' else hma 
    macd = request.GET.get('macd', '12,26,9')
    macd = '12,6,26' if macd == '0' else macd
    supertrend_length = request.GET.get('supertrendLength', '14')
    supertrend_multiplier = request.GET.get('supertrendMultiplier', '3')
    
    # Get Keltner Channel parameters
    keltner_ema_length = request.GET.get('keltnerEmaLength', '20')
    keltner_atr_length = request.GET.get('keltnerAtrLength', '14')
    keltner_multiplier = request.GET.get('keltnerMultiplier', '2')
    
    logger.info(f"Received request with parameters - Timeframe: {timeframe}, EMA: {ema}, SMA: {sma}, HMA: {hma}, MACD: {macd}, "
                f"Supertrend Length: {supertrend_length}, Supertrend Multiplier: {supertrend_multiplier}, "
                f"Keltner EMA Length: {keltner_ema_length}, Keltner ATR Length: {keltner_atr_length}, Keltner Multiplier: {keltner_multiplier}")

    # Pass the parameters to the stream generator
    response = StreamingHttpResponse(
        generate_dynamic_stream(
            timeframe, ema, sma, hma, macd, 
            supertrend_length, supertrend_multiplier,
            keltner_ema_length, keltner_atr_length, keltner_multiplier
        ),
        content_type='text/event-stream'
    )
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response

async def fetch_latest_data(ticker_symbol, timeframe='1', ema='10', sma='10', hma='10', macd='12,26,9', supertrend_length='14', supertrend_multiplier='3', keltner_ema_length='20', keltner_atr_length='14', keltner_multiplier='2'):
    """Fetch the latest data for a given ticker symbol."""
    try:
        logger.info(f"Fetching data for {ticker_symbol} with parameters - Timeframe: {timeframe}, EMA: {ema}, SMA: {sma}, HMA: {hma}, MACD: {macd}, "
                    f"Supertrend Length: {supertrend_length}, Supertrend Multiplier: {supertrend_multiplier}, "
                    f"Keltner EMA Length: {keltner_ema_length}, Keltner ATR Length: {keltner_atr_length}, Keltner Multiplier: {keltner_multiplier}")
        # Use sync_to_async to wrap the database operation
        data = await sync_to_async(_fetch_data_from_db)(
            ticker_symbol, timeframe, ema, sma, hma, macd, 
            supertrend_length, supertrend_multiplier, 
            keltner_ema_length, keltner_atr_length, keltner_multiplier
        )
        if data:
            logger.info(f"Fetched data for {ticker_symbol}: {data}")
        else:
            logger.warning(f"No data fetched for {ticker_symbol}")
        return data
    except Exception as e:
        logger.error(f"Error fetching data for {ticker_symbol}: {str(e)}")
        return None

def _fetch_data_from_db(ticker_symbol, timeframe='1', ema='10', sma='10', hma='10', macd='12,26,9', supertrend_length='14', supertrend_multiplier='3', keltner_ema_length='20', keltner_atr_length='14', keltner_multiplier='2'):
    with connection.cursor() as cursor:
        table_name = f"{ticker_symbol}_future_historical_data"
        
        if timeframe == '5':
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
                LIMIT 500
            """
        elif timeframe == '15':
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
                LIMIT 500
            """
        elif timeframe == '30':
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
                LIMIT 500
            """
        elif timeframe == '60':
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
                LIMIT 500
            """
        elif timeframe == '240':
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
                LIMIT 500
            """
        elif timeframe == '1440':
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
                LIMIT 500
            """
        else:
            query = f"""
                SELECT datetime, open_price, high_price, low_price, 
                       close_price, volume
                FROM "{table_name}"
                ORDER BY datetime DESC
                LIMIT 500
            """
        
        cursor.execute(query)
        columns = [col[0] for col in cursor.description]
        data = cursor.fetchall()
        if data:
            daily_data = _fetch_daily_data_from_db(ticker_symbol)
            macd_fast = int(macd.split(',')[0])
            macd_slow = int(macd.split(',')[1])
            macd_signal = int(macd.split(',')[2])
            indicators = calculate_indicators(
                data, 
                daily_data,
                ema_length=int(ema), 
                sma_length=int(sma), 
                hma_length=int(hma), 
                macd_fast=macd_fast, 
                macd_slow=macd_slow, 
                macd_signal=macd_signal, 
                supertrend_length=int(supertrend_length), 
                supertrend_multiplier=float(supertrend_multiplier), 
                keltner_ema_length=int(keltner_ema_length), 
                keltner_atr_length=int(keltner_atr_length), 
                keltner_multiplier=float(keltner_multiplier)
            )

            return {
                'ticker_symbol': ticker_symbol,
                **indicators,
                'bias': calculate_bias(data[-1], None, None)  # Assuming bias calculation is independent
            }
        return None


def calculate_bias(latest_data, previous_data, swings):
    """Determine market bias"""
    if not latest_data or not previous_data:
        return 'NEUTRAL'
    
    # Ensure latest_data and previous_data are tuples or lists
    if isinstance(latest_data, (list, tuple)) and isinstance(previous_data, (list, tuple)):
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
    else:
        logger.error("Invalid data format for bias calculation")
        return 'NEUTRAL'

async def generate_dynamic_stream(timeframe='1', ema='10', sma='10', hma='10', macd='12,26,9', supertrend_length='14', supertrend_multiplier='3', keltner_ema_length='20', keltner_atr_length='14', keltner_multiplier='2'):
    while True:
        try:
            logger.info(f"Generating stream with parameters - Timeframe: {timeframe}, EMA: {ema}, SMA: {sma}, HMA: {hma}, MACD: {macd}, Supertrend Length: {supertrend_length}, Supertrend Multiplier: {supertrend_multiplier}, Keltner EMA Length: {keltner_ema_length}, Keltner ATR Length: {keltner_atr_length}, Keltner Multiplier: {keltner_multiplier}")
            # Get all tickers
            tickers = await sync_to_async(list)(TickerBase.objects.all())
            formatted_data = []

            for ticker in tickers:
                # Fetch data based on the timeframe and indicators
                data = await fetch_latest_data(
                    ticker.ticker_symbol, timeframe, ema, sma, hma, macd, 
                    supertrend_length, supertrend_multiplier,
                    keltner_ema_length, keltner_atr_length, keltner_multiplier
                )
                if data:
                    formatted_data.append(data)

            if formatted_data:
                yield f"data: {json.dumps(formatted_data, cls=DjangoJSONEncoder)}\n\n"
            else:
                yield f"data: {json.dumps({'message': 'No data available'}, cls=DjangoJSONEncoder)}\n\n"

            # Log the timeframe and indicators being used
            logger.debug(f"Streaming data with timeframe: {timeframe}, EMA: {ema}, SMA: {sma}, HMA: {hma}, MACD: {macd}, Supertrend Length: {supertrend_length}, Supertrend Multiplier: {supertrend_multiplier}, Keltner EMA Length: {keltner_ema_length}, Keltner ATR Length: {keltner_atr_length}, Keltner Multiplier: {keltner_multiplier}")
            await asyncio.sleep(1)  # Update every second

        except Exception as e:
            logger.error(f"Error in generate_dynamic_stream: {str(e)}")
            yield f"data: {json.dumps({'error': str(e)}, cls=DjangoJSONEncoder)}\n\n"
            await asyncio.sleep(1)

def calculate_supertrend(data, period=10, multiplier=3):
    """Calculate Supertrend"""
    if len(data) < period:
        return None

    atr = calculate_atr(data, period)
    supertrend = []
    hl2 = [(d[2] + d[3]) / 2 for d in data]  # (High + Low) / 2

    for i in range(period, len(data)):
        upper_band = hl2[i] + (multiplier * atr[i - period])
        lower_band = hl2[i] - (multiplier * atr[i - period])

        if i == period:
            supertrend.append(lower_band if data[i][4] > upper_band else upper_band)
        else:
            if data[i][4] > supertrend[-1]:
                supertrend.append(max(lower_band, supertrend[-1]))
            else:
                supertrend.append(min(upper_band, supertrend[-1]))

    return "Bullish" if data[-1][4] > supertrend[-1] else "Bearish"

def _fetch_daily_data_from_db(ticker_symbol):
    """Fetch daily candle data for a ticker symbol specifically for pivot calculations."""
    with connection.cursor() as cursor:
        table_name = f"{ticker_symbol}_future_daily_historical_data"
        
        # Always fetch daily data regardless of user-selected timeframe
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
            LIMIT 30  -- Get the last 30 days for pivot calculations
        """
        
        cursor.execute(query)
        data = cursor.fetchall()
        return data

