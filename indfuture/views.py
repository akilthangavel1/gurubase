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


def indicator_future(request):
    logger.info("Rendering indicator_future template")
    return render(request, 'indfuture/indicator_future.html')


def future_dynamic_data(request):
    return render(request, 'ddfuture/dynamic_data_future.html')


def calculate_indicators(data, ema_length=10, sma_length=10, hma_length=10, macd_fast=12, macd_slow=26, macd_signal=9, supertrend_length=14, supertrend_multiplier=3):
   
    # print(f"Calculating indicators with parameters - EMA: {ema_length}, SMA: {sma_length}, HMA: {hma_length}, MACD: {macd_fast},{macd_slow},{macd_signal}")
    df = pd.DataFrame(data, columns=['datetime', 'open', 'high', 'low', 'close', 'volume'])
    df['datetime'] = pd.to_datetime(df['datetime'])

    # Sort the DataFrame by 'datetime' in ascending order
    df = df.sort_values(by='datetime', ascending=True)


    df['ema'] = ta.ema(df['close'], length=ema_length)

    # Calculate SMA
    df['sma'] = ta.sma(df['close'], length=sma_length)
    
    # Calculate HMA
    df['hma'] = ta.hma(df['close'], length=hma_length)

    macd = ta.macd(df['close'], fast=macd_fast, slow=macd_slow, signal=macd_signal)
    macd_inside_parm = "MACD_"+str(macd_slow)+"_"+ str(macd_fast) +"_"+ str(macd_signal)
    df['macd'] = macd[macd_inside_parm]
    macd_signal_inside_parm = "MACDs_"+str(macd_slow)+"_"+ str(macd_fast) +"_"+ str(macd_signal)
    df['signal_line'] = macd[macd_signal_inside_parm]

    # Calculate Supertrend
    supertrend = ta.supertrend(df['high'], df['low'], df['close'], length=supertrend_length, multiplier=supertrend_multiplier)
    df['supertrend'] = supertrend['SUPERT_'+str(supertrend_length)+"_"+str(supertrend_multiplier)]

    # Calculate Awesome Oscillator
    df['ao'] = ta.ao(df['high'], df['low'])

    # Calculate Keltner Channels
    keltner = ta.kc(df['high'], df['low'], df['close'], length=20, scalar=2.0)
    df['keltner_upper'] = keltner['KCUe_20_2.0']
    df['keltner_middle'] = keltner['KCBe_20_2.0']
    df['keltner_lower'] = keltner['KCLe_20_2.0']
    # Calculate Classic Pivot Points manually
    df['pivot'] = (df['high'] + df['low'] + df['close']) / 3

    df['r1'] = 2 * df['pivot'] - df['low']
    df['s1'] = 2 * df['pivot'] - df['high']
    df['r2'] = df['pivot'] + (df['high'] - df['low'])
    df['s2'] = df['pivot'] - (df['high'] - df['low'])
    df['r3'] = df['high'] + 2 * (df['pivot'] - df['low'])
    df['s3'] = df['low'] - 2 * (df['high'] - df['pivot'])

    # Calculate Camarilla Pivot Points
    df['camarilla_r1'] = df['close'] + (df['high'] - df['low']) * 1.1 / 12
    df['camarilla_r2'] = df['close'] + (df['high'] - df['low']) * 1.1 / 6
    df['camarilla_r3'] = df['close'] + (df['high'] - df['low']) * 1.1 / 4
    df['camarilla_r4'] = df['close'] + (df['high'] - df['low']) * 1.1 / 2
    df['camarilla_s1'] = df['close'] - (df['high'] - df['low']) * 1.1 / 12
    df['camarilla_s2'] = df['close'] - (df['high'] - df['low']) * 1.1 / 6
    df['camarilla_s3'] = df['close'] - (df['high'] - df['low']) * 1.1 / 4
    df['camarilla_s4'] = df['close'] - (df['high'] - df['low']) * 1.1 / 2

    # Convert 'datetime' column to datetime type if it's not already
    # df['datetime'] = pd.to_datetime(df['datetime'])

    # # Sort the DataFrame by 'datetime' in ascending order
    # df = df.sort_values(by='datetime', ascending=True)

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
    logger.info(f"Received request with parameters - Timeframe: {timeframe}, EMA: {ema}, SMA: {sma}, HMA: {hma}, MACD: {macd}, Supertrend Length: {supertrend_length}, Supertrend Multiplier: {supertrend_multiplier}")

    # Pass the parameters to the stream generator
    response = StreamingHttpResponse(
        generate_dynamic_stream(timeframe, ema, sma, hma, macd, supertrend_length, supertrend_multiplier),
        content_type='text/event-stream'
    )
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response

async def fetch_latest_data(ticker_symbol, timeframe='1', ema='10', sma='10', hma='10', macd='12,26,9', supertrend_length='14', supertrend_multiplier='3'):
    """Fetch the latest data for a given ticker symbol."""
    try:
        logger.info(f"Fetching data for {ticker_symbol} with parameters - Timeframe: {timeframe}, EMA: {ema}, SMA: {sma}, HMA: {hma}, MACD: {macd}, Supertrend Length: {supertrend_length}, Supertrend Multiplier: {supertrend_multiplier}")
        # Use sync_to_async to wrap the database operation
        data = await sync_to_async(_fetch_data_from_db)(ticker_symbol, timeframe, ema, sma, hma, macd, supertrend_length, supertrend_multiplier)
        if data:
            logger.info(f"Fetched data for {ticker_symbol}: {data}")
        else:
            logger.warning(f"No data fetched for {ticker_symbol}")
        return data
    except Exception as e:
        logger.error(f"Error fetching data for {ticker_symbol}: {str(e)}")
        return None

def _fetch_data_from_db(ticker_symbol, timeframe='1', ema='10', sma='10', hma='10', macd='12,26,9', supertrend_length='14', supertrend_multiplier='3'):
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
                LIMIT 700
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
            # Convert data to DataFrame and calculate indicators
            macd_fast = int(macd.split(',')[0])
            macd_slow = int(macd.split(',')[1])
            macd_signal = int(macd.split(',')[2])
            indicators = calculate_indicators(data, ema_length=int(ema), sma_length=int(sma), hma_length=int(hma), macd_fast=macd_fast, macd_slow=macd_slow, macd_signal=macd_signal, supertrend_length=int(supertrend_length), supertrend_multiplier=float(supertrend_multiplier))
            
            
            # indicators = calculate_indicators(
            #     data,
            #     ema_length=int(ema),
            #     sma_length=int(sma),
            #     hma_length=int(hma),
            # )

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

async def generate_dynamic_stream(timeframe='1', ema='10', sma='10', hma='10', macd='12,26,9', supertrend_length='14', supertrend_multiplier='3'):
    while True:
        try:
            logger.info(f"Generating stream with parameters - Timeframe: {timeframe}, EMA: {ema}, SMA: {sma}, HMA: {hma}, MACD: {macd}, Supertrend Length: {supertrend_length}, Supertrend Multiplier: {supertrend_multiplier}")
            # Get all tickers
            tickers = await sync_to_async(list)(TickerBase.objects.all())
            formatted_data = []

            for ticker in tickers:
                # Fetch data based on the timeframe and indicators
                data = await fetch_latest_data(ticker.ticker_symbol, timeframe, ema, sma, hma, macd, supertrend_length, supertrend_multiplier)
                if data:
                    formatted_data.append(data)

            if formatted_data:
                yield f"data: {json.dumps(formatted_data, cls=DjangoJSONEncoder)}\n\n"
            else:
                yield f"data: {json.dumps({'message': 'No data available'}, cls=DjangoJSONEncoder)}\n\n"

            # Log the timeframe and indicators being used
            logger.debug(f"Streaming data with timeframe: {timeframe}, EMA: {ema}, SMA: {sma}, HMA: {hma}, MACD: {macd}, Supertrend Length: {supertrend_length}, Supertrend Multiplier: {supertrend_multiplier}")
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

