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
from .fyers_functions import get_stock_quotes
from django.db import connection
import logging
from django.contrib import messages
from django.contrib.auth.decorators import login_required

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
    return render(request, 'dashboard/login.html')

def portfolio(request):
    return render(request, 'dashboard/portfolio.html')

def register(request):
    return render(request, 'dashboard/register.html')

def trending_stocks(request):
    return render(request, 'dashboard/trending stocks.html')

def stocks(request):
    """View for the stock screener page"""
    return render(request, 'dashboard/stocks.html')

def futures(request):
    """View for the futures page"""
    return render(request, 'dashboard/futures.html')

def future_scanner(request):
    return render(request, 'dashboard/future_scanner.html')

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



async def generate_event_stream():
    while True:
        try:
            tickers = await get_tickers()
            ticker_list = []
            time.sleep(1)
            for ticker in tickers:
                try:
                    symbols = ["NSE:SBIN-EQ", "NSE:RELIANCE-EQ", "NSE:TCS-EQ"] 
                    response = get_stock_quotes(symbols)
                    

                    # hist_data = await get_hist_data()

                #     hist_data = await get_hist_data(ticker.ticker_symbol)
                #     tick_data = await get_tick_data(ticker.ticker_symbol)
                    
                #     # Process historical data
                #     hist_df = pd.DataFrame(hist_data).drop('id', axis=1)
                #     hist_df.rename(columns={
                #         'open_price': 'open',
                #         'high_price': 'high',
                #         'low_price': 'low',
                #         'close_price': 'close'
                #     }, inplace=True)
                #     hist_df.set_index('datetime', inplace=True)
                    
                #     # Process tick data
                #     tick_df = pd.DataFrame(tick_data)
                #     tick_df['timestamp'] = tick_df['timestamp'].dt.floor('min')
                #     tick_ohlc_df = tick_df.groupby('timestamp').agg(
                #         open=('ltp', 'first'),
                #         high=('ltp', 'max'),
                #         low=('ltp', 'min'),
                #         close=('ltp', 'last')
                #     ).reset_index()
                #     tick_ohlc_df['volume'] = 0
                #     tick_ohlc_df.set_index('timestamp', inplace=True)
                #     tick_ohlc_df.index.name = 'datetime'

                #     # Combine historical and tick data
                #     hist_df.reset_index(inplace=True)
                #     tick_ohlc_df.reset_index(inplace=True)
                #     df = pd.concat([hist_df, tick_ohlc_df], ignore_index=True)
                #     df['datetime'] = pd.to_datetime(df['datetime'])
                #     df.set_index('datetime', inplace=True)
                    
                #     # Calculate daily aggregates
                #     daily_df = df.resample('D').agg({
                #         'open': 'first',
                #         'high': 'max',
                #         'low': 'min',
                #         'close': 'last',
                #         'volume': 'sum'
                #     }).dropna()
                    
                #     # Calculate changes and get latest values
                #     daily_df = daily_df.reset_index()
                #     latest_close, daily_change, weekly_change = calculate_changes(daily_df)
                #     previous_day_data = daily_df.iloc[-2]
                #     latest_data = daily_df.iloc[-1]

                #     ticker_data = {
                #         "name": ticker.name,
                #         "symbol": ticker.ticker_symbol,
                #         "sector": ticker.sector,
                #         "sub_sector": ticker.sub_sector,
                #         "market_cap": ticker.market_cap,
                #         "ltp": latest_close,
                #         "daily_change": daily_change,
                #         "weekly_change": weekly_change,
                #         "previous_day_open": float(previous_day_data['open']),
                #         "previous_day_high": float(previous_day_data['high']),
                #         "previous_day_low": float(previous_day_data['low']),
                #         "previous_day_close": float(previous_day_data['close']),
                #         "latest_open": float(latest_data['open']),
                #         "latest_high": float(latest_data['high']),
                #         "latest_low": float(latest_data['low']),
                #     }
                    
                #     ticker_list.append(ticker_data)
                    
                except Exception as e:
                    print(f"Error processing {ticker.ticker_symbol}: {str(e)}")
                    continue

            # yield f"data: {json.dumps(ticker_list)}\n\n"
        except Exception as e:
            print(f"Exception occurred: {str(e)}")
            yield f"data: Exception occurred: {str(e)}\n\n"
        
        await asyncio.sleep(1)

async def sse_stocks_data(request):
    """SSE endpoint for real-time stock updates"""
    response = StreamingHttpResponse(
        generate_event_stream(),
        content_type='text/event-stream'
    )
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response

def view_historical_data(request, ticker_symbol=None):
    try:
        # Get all tickers if no specific ticker is provided
        if ticker_symbol:
            tickers = TickerBase.objects.filter(ticker_symbol=ticker_symbol)
        else:
            tickers = TickerBase.objects.all()
        
        all_data = {}
        
        for ticker in tickers:
            table_name = f"{ticker.ticker_symbol}_future_historical_data"
            
            # Fetch data from the specific table
            with connection.cursor() as cursor:
                try:
                    # First check if table exists - fixed query syntax
                    cursor.execute("""
                        SELECT EXISTS (
                            SELECT 1 
                            FROM information_schema.tables 
                            WHERE table_name = %s
                        )
                    """, [table_name.lower()])  # PostgreSQL table names are lowercase
                    
                    table_exists = cursor.fetchone()[0]
                    
                    if not table_exists:
                        logger.error(f"Table {table_name} does not exist")
                        continue
                    
                    # Fixed query syntax - using proper string formatting for table name
                    query = """
                        SELECT datetime, open_price, high_price, low_price, 
                               close_price, volume 
                        FROM "{}"
                        ORDER BY datetime DESC
                        LIMIT 100
                    """.format(table_name)
                    
                    cursor.execute(query)
                    
                    columns = [col[0] for col in cursor.description]
                    data = cursor.fetchall()
                    
                    # Convert to list of dictionaries
                    ticker_data = []
                    for row in data:
                        ticker_data.append(dict(zip(columns, row)))
                    
                    all_data[ticker.ticker_symbol] = ticker_data
                    
                except Exception as db_error:
                    logger.error(f"Database error for {table_name}: {str(db_error)}")
                    continue
        
        if not all_data:
            return render(request, 'dashboard/historical_data.html', {
                'error': "No data available or tables not found",
                'tickers': tickers
            })
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'data': all_data})
        else:
            return render(request, 'dashboard/historical_data.html', {
                'data': all_data,
                'tickers': tickers
            })
            
    except Exception as e:
        logger.error(f"View error: {str(e)}")
        return render(request, 'dashboard/historical_data.html', {
            'error': f"An error occurred: {str(e)}"
        })
    

def ticker_list(request):
    tickers = TickerBase.objects.all().order_by('ticker_sector', 'ticker_name')
    context = {
        'tickers': tickers,
        'sectors': TickerBase.SECTOR_CHOICES,
        'market_caps': TickerBase.MARKET_CAP_CHOICES
    }
    return render(request, 'dashboard/ticker_list.html', context)


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
    