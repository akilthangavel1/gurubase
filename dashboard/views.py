from django.shortcuts import render, redirect, get_object_or_404
from fyers_apiv3 import fyersModel
from django.conf import settings
import json
import os
from django.http import JsonResponse, StreamingHttpResponse
import asyncio
import pandas as pd
from asgiref.sync import sync_to_async
from .models import TickerBase
import time
from .fyers_functions import get_live_data
from django.db import connection
import logging
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import login as auth_login, authenticate
from django.core.serializers.json import DjangoJSONEncoder
from django.http import HttpResponse

logger = logging.getLogger(__name__)

# Create your views here.


def index(request):
    try:
        # Initialize Fyers API client using settings
        client_id = settings.FYERS_CONFIG['client_id']
        access_token = settings.FYERS_CONFIG['access_token']
        fyers = fyersModel.FyersModel(client_id=client_id, is_async=False, token=access_token, log_path="")
        
        # Fetch historical data
        data = {
            "symbol": "NSE:AARTIIND24DECFUT",
            "resolution": "D",
            "date_format": "0",
            "range_from": "1690895316",
            "range_to": "1691068173",
            "cont_flag": "1"
        }
        
        historical_data = fyers.history(data=data)
        
        # Prepare context to send to template
        context = {
            'market_data': historical_data
        }
        
    except Exception as e:
        # Handle any errors gracefully
        context = {
            'error': str(e)
        }
    
    return render(request, 'dashboard/index.html', context)

def features(request):
    return render(request, 'dashboard/features.html')

def live_stocks(request):
    return render(request, 'dashboard/live-stocks.html')

def login(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        user = authenticate(request, username=email, password=password)
        
        if user is not None:
            auth_login(request, user)
            return redirect('index')
        else:
            messages.error(request, 'Invalid email or password')
    
    return render(request, 'dashboard/login.html')

def portfolio(request):
    return render(request, 'dashboard/portfolio.html')

def register(request):
    return render(request, 'dashboard/register.html')

def trending_stocks(request):
    return render(request, 'dashboard/trending stocks.html')

def stocks(request):
    return render(request, 'dashboard/stocks.html')

def futures(request):
    return render(request, 'dashboard/futures.html')

def future_scanner(request):
    # """View for the future scanner page with real-time updates"""
    # return render(request, 'dashboard/future_scanner.html', {
    #     'update_interval': 1000  # 1 second interval for updates
    # })
    return HttpResponse("Validation Pending")

def options(request):
    """View for the options page"""
    return render(request, 'dashboard/options.html')



def get_stocks_data(request):
    # stocks = Stock.objects.all()
    data = []
    
    for stock in stocks:
        data.append({
            'name': stock.name,
            'ticker': stock.ticker,
            'open': float(stock.open),
            'high': float(stock.high),
            'low': float(stock.low),
            'close': float(stock.close),
        })
    
    return JsonResponse(data, safe=False)

@sync_to_async
def get_tickers():
    return list(TickerBase.objects.all())

async def get_hist_data(symbol):
    """Async function to get historical data"""
    # Implement your historical data fetching logic here
    pass

async def get_tick_data(symbol):
    """Async function to get tick data"""
    # Implement your tick data fetching logic here
    pass

def calculate_changes(df):
    """Calculate daily and weekly changes"""
    latest_close = df.iloc[-1]['close']
    daily_change = ((df.iloc[-1]['close'] - df.iloc[-2]['close']) / df.iloc[-2]['close']) * 100
    weekly_change = ((df.iloc[-1]['close'] - df.iloc[-5]['close']) / df.iloc[-5]['close']) * 100 if len(df) >= 5 else 0
    return latest_close, daily_change, weekly_change



@sync_to_async
def get_live_data_async():
    return get_live_data()

async def generate_event_stream():
    while True:
        try:
            # Check if current time is within market hours
            current_time = pd.Timestamp.now('Asia/Kolkata')
            market_start = current_time.replace(hour=9, minute=0, second=0)
            market_end = current_time.replace(hour=15, minute=45, second=0)
            
            # Check if it's a weekday (Monday = 0, Sunday = 6)
            is_weekday = current_time.weekday() < 5
            
            if not is_weekday or not (market_start <= current_time <= market_end):
                yield f"data: {json.dumps({'message': 'Market is closed'}, cls=DjangoJSONEncoder)}\n\n"
                await asyncio.sleep(60)  # Check every minute during off-market hours
                continue
                
            response = await get_live_data_async()
            if response and response.get('s') == 'ok' and 'd' in response:
                data = response['d']
                formatted_data = []
                
                for stock_data in data:
                    v = stock_data.get('v', {})
                    formatted_data.append({
                        'symbol': stock_data['n'].split(':')[1],  # Remove 'NSE:' prefix
                        'last_price': v.get('lp', '-'),
                        'change': v.get('ch', '-'),
                        'change_percent': v.get('chp', '-'),
                        'high': v.get('high_price', '-'),
                        'low': v.get('low_price', '-'),
                        'volume': v.get('volume', '-'),
                        'open': v.get('open_price', '-'),
                        'prev_close': v.get('prev_close_price', '-'),
                        'bid': v.get('bid', '-'),
                        'ask': v.get('ask', '-')
                    })
                yield f"data: {json.dumps(formatted_data, cls=DjangoJSONEncoder)}\n\n"
            await asyncio.sleep(1)
        except Exception as e:
            logger.error(f"Error in generate_event_stream: {str(e)}")
            yield f"data: {json.dumps({'error': str(e)}, cls=DjangoJSONEncoder)}\n\n"
            await asyncio.sleep(1)

def sse_stocks_data(request):
    """SSE endpoint for real-time stock updates"""
    response = StreamingHttpResponse(
        generate_event_stream(),
        content_type='text/event-stream'
    )
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response


def ticker_list_view(request):
    tickers = TickerBase.objects.all().order_by('ticker_sector', 'ticker_name')
    context = {
        'tickers': tickers,
        'sectors': TickerBase.SECTOR_CHOICES,
        'market_caps': TickerBase.MARKET_CAP_CHOICES
    }
    return render(request, 'dashboard/ticker_list.html', context)

def historical_data(request):
    """Display list of all tickers"""
    tickers = TickerBase.objects.all().order_by('ticker_sector', 'ticker_name')
    return render(request, 'dashboard/historical_data_list.html', {'tickers': tickers})

def historical_data_detail(request, ticker_symbol):
    """Display historical data for a specific ticker"""
    ticker = get_object_or_404(TickerBase, ticker_symbol=ticker_symbol)
    
    try:
        table_name = f"{ticker_symbol}_future_historical_data"
        
        with connection.cursor() as cursor:
            # Check if table exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT 1 
                    FROM information_schema.tables 
                    WHERE table_name = %s
                )
            """, [table_name.lower()])
            
            if not cursor.fetchone()[0]:
                return render(request, 'dashboard/historical_data_detail.html', {
                    'ticker': ticker,
                    'error': "No historical data available for this ticker"
                })
            
            # Fetch data
            query = """
                SELECT datetime, open_price, high_price, low_price, 
                       close_price, volume 
                FROM "{}"
                ORDER BY datetime DESC
                LIMIT 100
            """.format(table_name)
            
            cursor.execute(query)
            columns = [col[0] for col in cursor.description]
            data = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
            return render(request, 'dashboard/historical_data_detail.html', {
                'ticker': ticker,
                'data': data
            })
            
    except Exception as e:
        return render(request, 'dashboard/historical_data_detail.html', {
            'ticker': ticker,
            'error': f"An error occurred: {str(e)}"
        })

def ticker_create(request):
    if request.method == 'POST':
        try:
            ticker_data = {
                'ticker_name': request.POST['ticker_name'].strip(),
                'ticker_symbol': request.POST['ticker_symbol'].strip().upper(),
                'ticker_sector': request.POST['ticker_sector'],
                'ticker_sub_sector': request.POST.get('ticker_sub_sector', '').strip() or None,
                'ticker_market_cap': request.POST['ticker_market_cap']
            }
            
            ticker = TickerBase.objects.create(**ticker_data)
            messages.success(request, f'Ticker {ticker.ticker_name} created successfully!')
            return redirect('ticker_list')
            
        except Exception as e:
            messages.error(request, f'Error creating ticker: {str(e)}')
    
    context = {
        'sectors': TickerBase.SECTOR_CHOICES,
        'market_caps': TickerBase.MARKET_CAP_CHOICES
    }
    return render(request, 'dashboard/ticker_form.html', context)


def ticker_update(request, pk):
    ticker = get_object_or_404(TickerBase, pk=pk)
    
    if request.method == 'POST':
        try:
            ticker.ticker_name = request.POST['ticker_name'].strip()
            ticker.ticker_symbol = request.POST['ticker_symbol'].strip().upper()
            ticker.ticker_sector = request.POST['ticker_sector']
            ticker.ticker_sub_sector = request.POST.get('ticker_sub_sector', '').strip() or None
            ticker.ticker_market_cap = request.POST['ticker_market_cap']
            
            ticker.save()
            messages.success(request, f'Ticker {ticker.ticker_name} updated successfully!')
            return redirect('ticker_list')
            
        except Exception as e:
            messages.error(request, f'Error updating ticker: {str(e)}')
    
    context = {
        'ticker': ticker,
        'sectors': TickerBase.SECTOR_CHOICES,
        'market_caps': TickerBase.MARKET_CAP_CHOICES
    }
    return render(request, 'dashboard/ticker_form.html', context)


def ticker_delete(request, pk):
    ticker = get_object_or_404(TickerBase, pk=pk)
    
    if request.method == 'POST':
        try:
            ticker_name = ticker.ticker_name
            ticker.delete()
            messages.success(request, f'Ticker {ticker_name} deleted successfully!')
        except Exception as e:
            messages.error(request, f'Error deleting ticker: {str(e)}')
        return redirect('ticker_list')
    
    context = {'ticker': ticker}
    return render(request, 'dashboard/ticker_confirm_delete.html', context)

@login_required
def profile(request):
    return render(request, 'dashboard/profile.html')

def live_data(request):
    """View for displaying live stock data using SSE"""
    tickers = TickerBase.objects.all()
    context = {
        'tickers': tickers,
    }
    return render(request, 'dashboard/live_data.html', context)

def is_staff(user):
    return user.is_staff

# @login_required
# @user_passes_test(is_staff)
def clear_ticker_data(request):
    if request.method == 'POST':
        ticker_symbol = request.POST.get('ticker_symbol')
        try:
            with connection.cursor() as cursor:
                # Clear historical data
                table_name = f"{ticker_symbol}_historical_data"
                cursor.execute(f"TRUNCATE TABLE {table_name}")
                
                # Clear future historical data
                future_table_name = f"{ticker_symbol}_future_historical_data"
                cursor.execute(f"TRUNCATE TABLE {future_table_name}")
                
                # Clear future daily historical data
                future_daily_table_name = f"{ticker_symbol}_future_daily_historical_data"
                cursor.execute(f"TRUNCATE TABLE {future_daily_table_name}")
                
            messages.success(request, f'Successfully cleared data for {ticker_symbol}')
        except Exception as e:
            messages.error(request, f'Error clearing data: {str(e)}')
        
    return redirect('ticker_list')

# @login_required
# @user_passes_test(is_staff)
def data_management(request):
    tickers = TickerBase.objects.all()
    ticker_data = []
    
    with connection.cursor() as cursor:
        for ticker in tickers:
            # Get historical data count
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {ticker.ticker_symbol}_historical_data")
                historical_count = cursor.fetchone()[0]
            except:
                historical_count = 0
                
            # Get future historical data count
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {ticker.ticker_symbol}_future_historical_data")
                future_count = cursor.fetchone()[0]
            except:
                future_count = 0
                
            # Get future daily historical data count
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {ticker.ticker_symbol}_future_daily_historical_data")
                future_daily_count = cursor.fetchone()[0]
            except:
                future_daily_count = 0
                
            ticker_data.append({
                'ticker_symbol': ticker.ticker_symbol,
                'historical_count': historical_count,
                'future_count': future_count,
                'future_daily_count': future_daily_count
            })
    
    return render(request, 'dashboard/data_management.html', {
        'tickers': ticker_data
    })

# @login_required
def clear_all_data(request):
    if request.method == 'POST':
        try:
            # Get all tickers
            tickers = TickerBase.objects.all()
            
            with connection.cursor() as cursor:
                for ticker in tickers:
                    try:
                        # Clear historical data
                        table_name = f"{ticker.ticker_symbol}_historical_data"
                        cursor.execute(f"TRUNCATE TABLE {table_name}")
                        
                        # Clear future historical data
                        future_table_name = f"{ticker.ticker_symbol}_future_historical_data"
                        cursor.execute(f"TRUNCATE TABLE {future_table_name}")
                        
                        # Clear future daily historical data
                        future_daily_table_name = f"{ticker.ticker_symbol}_future_daily_historical_data"
                        cursor.execute(f"TRUNCATE TABLE {future_daily_table_name}")
                        
                    except Exception as e:
                        # Log the error but continue with other tickers
                        logger.error(f"Error clearing data for {ticker.ticker_symbol}: {str(e)}")
                        continue
                
            messages.success(request, 'Successfully cleared all ticker data')
        except Exception as e:
            messages.error(request, f'Error clearing data: {str(e)}')
    return redirect('data_management')

async def generate_future_scanner_stream():
    while True:
        try:
            # Check market hours
            current_time = pd.Timestamp.now('Asia/Kolkata')
            market_start = current_time.replace(hour=9, minute=0, second=0)
            market_end = current_time.replace(hour=15, minute=45, second=0)
            is_weekday = current_time.weekday() < 5
            
            # if not is_weekday or not (market_start <= current_time <= market_end):
            #     yield f"data: {json.dumps({'message': 'Market is closed'}, cls=DjangoJSONEncoder)}\n\n"
            #     await asyncio.sleep(60)
            #     continue

            # Get all tickers
            tickers = await sync_to_async(list)(TickerBase.objects.all())
            scanner_data = {}
            
            for ticker in tickers:
                try:
                    # Get historical data from database for calculations
                    historical_data = await get_historical_data_async(ticker.ticker_symbol)

                    if not historical_data.empty:
                        # Use the latest data point as current data
                        latest_data = historical_data.iloc[0]
                        
                        scanner_data[ticker.ticker_symbol] = {
                            'name': ticker.ticker_name,
                            'sector': ticker.ticker_sector,
                            'hourly_bars': await calculate_hourly_bars(latest_data, historical_data),
                            'daily_stats': await calculate_daily_stats(latest_data, historical_data),
                            'weekly_stats': await calculate_weekly_stats(latest_data, historical_data),
                            'monthly_stats': await calculate_monthly_stats(latest_data, historical_data),
                            'current_price': float(latest_data['close_price']),
                            'timestamp': current_time.isoformat()
                        }
                except Exception as e:
                    logger.error(f"Error processing ticker {ticker.ticker_symbol}: {str(e)}")
                    continue
            
            if scanner_data:
                yield f"data: {json.dumps(scanner_data, cls=DjangoJSONEncoder)}\n\n"
            else:
                yield f"data: {json.dumps({'message': 'No data available'}, cls=DjangoJSONEncoder)}\n\n"
                
            await asyncio.sleep(1)
            
        except Exception as e:
            logger.error(f"Error in generate_future_scanner_stream: {str(e)}")
            yield f"data: {json.dumps({'error': str(e)}, cls=DjangoJSONEncoder)}\n\n"
            await asyncio.sleep(1)

@sync_to_async
def get_historical_data_async(ticker_symbol, timeframe='1'):
    """Fetch historical data for calculations"""
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
                            SUM(volume) OVER w AS volume
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
            else:
                # For 1-minute timeframe, get raw data
                query = f"""
                    SELECT 
                        datetime,
                        open_price,
                        high_price,
                        low_price,
                        close_price,
                        volume
                    FROM "{table_name}"
                    WHERE datetime >= NOW() - INTERVAL '24 hours'
                    ORDER BY datetime DESC
                """
            
            logger.debug(f"Executing query on table: {table_name}")
            logger.debug(f"SQL Query: {query}")
            
            cursor.execute(query)
            columns = [col[0] for col in cursor.description]
            data = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
            df = pd.DataFrame(data)
            print(df)
            if not df.empty:
                # Rename interval_start to datetime for 5-minute data to maintain consistency
                if timeframe == '5':
                    df = df.rename(columns={'interval_start': 'datetime'})
                # Convert datetime to pandas datetime
                df['datetime'] = pd.to_datetime(df['datetime'])
                
            logger.info(f"Retrieved {len(df)} records for {ticker_symbol} with {timeframe}min timeframe")
            return df
            
    except Exception as e:
        logger.error(f"Error fetching historical data for {ticker_symbol}: {str(e)}")
        return pd.DataFrame()

async def calculate_hourly_bars(latest_data, historical_data):
    """Calculate hourly high/low bars using historical data"""
    current_date = pd.Timestamp.now('Asia/Kolkata').date()
    today_data = historical_data[historical_data['datetime'].dt.date == current_date]
    
    hourly_bars = {}
    for hour in range(9, 16):
        hour_data = today_data[
            (today_data['datetime'].dt.hour == hour)
        ]
        if not hour_data.empty:
            hourly_bars[f'{hour}_{hour+1}'] = {
                'high': float(hour_data['high_price'].max()),
                'low': float(hour_data['low_price'].min())
            }
        else:
            hourly_bars[f'{hour}_{hour+1}'] = {'high': 0, 'low': 0}
    
    return hourly_bars

async def calculate_daily_stats(latest_data, historical_data):
    """Calculate daily statistics using historical data"""
    try:
        # Last 30 minutes data
        last_30min = historical_data.head(6)  # Assuming 5-minute candles
        current_30min_top = last_30min['high_price'].max()
        current_30min_bottom = last_30min['low_price'].min()
        
        # Last 5 tops and bottoms in 30 mins
        tops = historical_data.nlargest(5, 'high_price')[['datetime', 'high_price']]
        bottoms = historical_data.nsmallest(5, 'low_price')[['datetime', 'low_price']]
        
        return {
            'current_30min_top': {
                'value': float(current_30min_top),
                'timestamp': last_30min.iloc[0]['datetime'].isoformat()
            },
            'current_30min_bottom': {
                'value': float(current_30min_bottom),
                'timestamp': last_30min.iloc[0]['datetime'].isoformat()
            },
            'last_5_tops': tops.to_dict('records'),
            'last_5_bottoms': bottoms.to_dict('records'),
            'day_tops': historical_data.nlargest(40, 'high_price')[['datetime', 'high_price']].to_dict('records'),
            'day_bottoms': historical_data.nsmallest(40, 'low_price')[['datetime', 'low_price']].to_dict('records')
        }
    except Exception as e:
        logger.error(f"Error in calculate_daily_stats: {str(e)}")
        return {}

async def calculate_weekly_stats(latest_data, historical_data):
    """Calculate weekly statistics"""
    try:
        # Current week data
        current_week = historical_data[
            historical_data['datetime'].dt.isocalendar().week == 
            pd.Timestamp.now('Asia/Kolkata').isocalendar().week
        ]
        
        return {
            'expiry_week': {
                'open': float(current_week.iloc[0]['open_price']) if not current_week.empty else 0,
                'high': float(current_week['high_price'].max()) if not current_week.empty else 0,
                'low': float(current_week['low_price'].min()) if not current_week.empty else 0,
                'close': float(current_week.iloc[-1]['close_price']) if not current_week.empty else 0,
                'vwap': calculate_vwap(current_week),
                'volume': int(current_week['volume'].sum()) if not current_week.empty else 0
            },
            'weekly_tops': historical_data.nlargest(16, 'high_price')[['datetime', 'high_price']].to_dict('records'),
            'weekly_bottoms': historical_data.nsmallest(16, 'low_price')[['datetime', 'low_price']].to_dict('records')
        }
    except Exception as e:
        logger.error(f"Error in calculate_weekly_stats: {str(e)}")
        return {}

async def calculate_monthly_stats(latest_data, historical_data):
    """Calculate monthly statistics"""
    try:
        monthly_tops = historical_data.nlargest(6, 'high_price')[['datetime', 'high_price']]
        monthly_bottoms = historical_data.nsmallest(6, 'low_price')[['datetime', 'low_price']]
        
        return {
            'month_tops': monthly_tops.head(3).to_dict('records'),
            'month_bottoms': monthly_bottoms.head(3).to_dict('records'),
            'highest_tops': monthly_tops.to_dict('records'),
            'lowest_bottoms': monthly_bottoms.to_dict('records')
        }
    except Exception as e:
        logger.error(f"Error in calculate_monthly_stats: {str(e)}")
        return {}

def calculate_vwap(data):
    """Calculate Volume Weighted Average Price"""
    try:
        if data.empty:
            return 0
        typical_price = (data['high_price'] + data['low_price'] + data['close_price']) / 3
        return float((typical_price * data['volume']).sum() / data['volume'].sum())
    except Exception:
        return 0

def sse_future_scanner(request):
    """SSE endpoint for real-time future scanner updates"""
    response = StreamingHttpResponse(
        generate_future_scanner_stream(),
        content_type='text/event-stream'
    )
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response
    
def future_technical_indicators(request):
    # return render(request, 'dashboard/future_technical_indicators.html')
    return HttpResponse("Validation Pending")



def future_dynamic_data(request):
    tickers = TickerBase.objects.all().order_by('ticker_name')
    return render(request, 'dashboard/future_dynamic_data.html', {'tickers': tickers})


def future_alerts(request):
    tickers = TickerBase.objects.all().order_by('ticker_name')
    return render(request, 'dashboard/future_alerts.html', {'tickers': tickers})

# def future_data_api(request):
#     """API endpoint for future data"""
#     # Add your logic here
#     return JsonResponse({'data': []})  # Return appropriate data

async def generate_future_dynamic_stream(timeframe):
    while True:
        try:
            # Get all tickers
            tickers = await sync_to_async(list)(TickerBase.objects.all())
            formatted_data = []

            for ticker in tickers:
                try:
                    # Get latest data with specified timeframe
                    historical_data = await get_historical_data_async(ticker.ticker_symbol, timeframe)
                    
                    if not historical_data.empty:
                        # Get current and previous candle data
                        current_candle = historical_data.iloc[0]
                        previous_candle = historical_data.iloc[1] if len(historical_data) > 1 else None
                        last_3_candles = historical_data.head(3).to_dict('records') if len(historical_data) >= 3 else []

                        # Calculate swing points (last 20 candles)
                        last_20_candles = historical_data.head(20)
                        swing_highs = last_20_candles.nlargest(3, 'high_price')['high_price'].tolist()
                        swing_lows = last_20_candles.nsmallest(3, 'low_price')['low_price'].tolist()

                        # Pad swing points if we don't have enough
                        while len(swing_highs) < 3:
                            swing_highs.append(None)
                        while len(swing_lows) < 3:
                            swing_lows.append(None)

                        ticker_data = {
                            'ticker_symbol': ticker.ticker_symbol,
                            'current_candle_open': float(current_candle['open_price']),
                            'current_candle_high': float(current_candle['high_price']),
                            'current_candle_low': float(current_candle['low_price']),
                            'current_candle_close': float(current_candle['close_price']),
                            'previous_candle_open': float(previous_candle['open_price']) if previous_candle is not None else None,
                            'previous_candle_high': float(previous_candle['high_price']) if previous_candle is not None else None,
                            'previous_candle_low': float(previous_candle['low_price']) if previous_candle is not None else None,
                            'previous_candle_close': float(previous_candle['close_price']) if previous_candle is not None else None,
                            'prev_swing_high_1': swing_highs[0],
                            'prev_swing_high_2': swing_highs[1],
                            'prev_swing_high_3': swing_highs[2],
                            'prev_swing_low_1': swing_lows[0],
                            'prev_swing_low_2': swing_lows[1],
                            'prev_swing_low_3': swing_lows[2],
                            'last_3_candles': last_3_candles,
                            'timestamp': current_candle['datetime'].isoformat()
                        }
                        formatted_data.append(ticker_data)

                except Exception as e:
                    logger.error(f"Error processing ticker {ticker.ticker_symbol}: {str(e)}")
                    continue

            if formatted_data:
                yield f"data: {json.dumps(formatted_data, cls=DjangoJSONEncoder)}\n\n"
            else:
                yield f"data: {json.dumps({'message': 'No data available'}, cls=DjangoJSONEncoder)}\n\n"

            # Update every second regardless of timeframe
            await asyncio.sleep(1)

        except Exception as e:
            logger.error(f"Error in generate_future_dynamic_stream: {str(e)}")
            yield f"data: {json.dumps({'error': str(e)}, cls=DjangoJSONEncoder)}\n\n"
            await asyncio.sleep(1)

def sse_future_dynamic_data(request):
    """SSE endpoint for real-time future dynamic data updates"""
    timeframe = request.GET.get('timeframe', '1')  # Default to 1-minute timeframe
    response = StreamingHttpResponse(
        generate_future_dynamic_stream(timeframe),
        content_type='text/event-stream'
    )
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response

def future_daily_data(request):
    """Display list of all tickers for future daily data selection"""
    tickers = TickerBase.objects.all().order_by('ticker_sector', 'ticker_name')
    return render(request, 'dashboard/future_daily_data_list.html', {'tickers': tickers})

def future_daily_data_detail(request, ticker_symbol):
    """Display future daily historical data for a specific ticker"""
    ticker = get_object_or_404(TickerBase, ticker_symbol=ticker_symbol)
    
    try:
        table_name = f"{ticker_symbol}_future_daily_historical_data"
        
        with connection.cursor() as cursor:
            # Check if table exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT 1 
                    FROM information_schema.tables 
                    WHERE table_name = %s
                )
            """, [table_name.lower()])
            
            if not cursor.fetchone()[0]:
                return render(request, 'dashboard/future_daily_data_detail.html', {
                    'ticker': ticker,
                    'error': "No future daily historical data available for this ticker"
                })
            
            # Fetch data
            query = """
                SELECT datetime, open_price, high_price, low_price, 
                       close_price, volume 
                FROM "{}"
                ORDER BY datetime DESC
                LIMIT 100
            """.format(table_name)
            
            cursor.execute(query)
            columns = [col[0] for col in cursor.description]
            data = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
            return render(request, 'dashboard/future_daily_data_detail.html', {
                'ticker': ticker,
                'data': data
            })
            
    except Exception as e:
        return render(request, 'dashboard/future_daily_data_detail.html', {
            'ticker': ticker,
            'error': f"An error occurred: {str(e)}"
        })
