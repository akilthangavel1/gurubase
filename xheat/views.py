from django.shortcuts import render
from django.http import JsonResponse
from django.db import connection
from dashboard.models import TickerBase
import pandas as pd
from datetime import datetime, timedelta
import json


def heatmap_view(request):
    """Main heatmap view that displays the heatmap visualization"""
    return render(request, 'xheat/heatmap.html')


def heatmap_data(request):
    """API endpoint that returns heatmap data for all stocks grouped by sector"""
    try:
        # Get index parameter (nifty50, nifty100, nifty500)
        index_filter = request.GET.get('index', 'nifty500')
        
        # Get all tickers with their sectors
        tickers = TickerBase.objects.all().select_related()
        
        # Filter tickers based on index if needed
        # You can add index filtering logic here based on market cap or other criteria
        
        # Calculate performance metrics for each ticker
        heatmap_data = []
        processed_count = 0
        
        for ticker in tickers:
            performance = calculate_performance_metrics(ticker.ticker_symbol)
            if performance:
                heatmap_data.append({
                    'ticker_symbol': ticker.ticker_symbol,
                    'ticker_name': ticker.ticker_name,
                    'sector': ticker.get_ticker_sector_display() if hasattr(ticker, 'get_ticker_sector_display') else ticker.ticker_sector,
                    'market_cap': ticker.get_ticker_market_cap_display() if hasattr(ticker, 'get_ticker_market_cap_display') else ticker.ticker_market_cap,
                    'daily_change': performance.get('daily_change', 0),
                    'weekly_change': performance.get('weekly_change', 0),
                    'monthly_change': performance.get('monthly_change', 0),
                    'volume': performance.get('volume', 0),
                    'current_price': performance.get('current_price', 0),
                })
                processed_count += 1
        
        # Group data by sector
        sectors = {}
        for item in heatmap_data:
            sector = item['sector']
            if sector not in sectors:
                sectors[sector] = []
            sectors[sector].append(item)
        
        return JsonResponse({
            'success': True,
            'data': sectors,
            'flat_data': heatmap_data,
            'count': processed_count
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


def calculate_performance_metrics(ticker_symbol):
    """Calculate performance metrics for a given ticker using Future Daily Historical Data"""
    try:
        # Use the future daily historical data table
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
                return None
            
            # Get recent daily data for performance calculations
            # Fetch more days to ensure we have trading days data
            query = f"""
                SELECT datetime, open_price, high_price, low_price, close_price, volume
                FROM "{table_name}"
                WHERE datetime >= NOW() - INTERVAL '60 days'
                ORDER BY datetime DESC
                LIMIT 100
            """
            
            cursor.execute(query)
            data = cursor.fetchall()
            
            if not data:
                return None
            
            # Convert to DataFrame for easier calculations
            df = pd.DataFrame(data, columns=['datetime', 'open_price', 'high_price', 'low_price', 'close_price', 'volume'])
            df['datetime'] = pd.to_datetime(df['datetime'])
            df = df.sort_values('datetime').reset_index(drop=True)
            
            if len(df) < 2:
                return None
            
            # Get current price (most recent close)
            current_price = df.iloc[-1]['close_price']
            current_volume = df.iloc[-1]['volume']
            
            # Calculate daily change (compared to previous trading day)
            daily_change = 0
            if len(df) >= 2:
                prev_price = df.iloc[-2]['close_price']
                daily_change = ((current_price - prev_price) / prev_price) * 100
            
            # Calculate weekly change (5-7 trading days ago)
            weekly_change = 0
            if len(df) >= 6:  # At least 6 days of data
                # Look for data around 5-7 trading days back
                week_ago_idx = min(5, len(df) - 2)  # 5 trading days back or max available
                week_ago_price = df.iloc[-(week_ago_idx + 1)]['close_price']
                weekly_change = ((current_price - week_ago_price) / week_ago_price) * 100
            
            # Calculate monthly change (20-25 trading days ago)
            monthly_change = 0
            if len(df) >= 21:  # At least 21 days of data
                # Look for data around 20 trading days back
                month_ago_idx = min(20, len(df) - 2)  # 20 trading days back or max available
                month_ago_price = df.iloc[-(month_ago_idx + 1)]['close_price']
                monthly_change = ((current_price - month_ago_price) / month_ago_price) * 100
            elif len(df) >= 11:  # Fallback to ~2 weeks
                month_ago_idx = min(10, len(df) - 2)
                month_ago_price = df.iloc[-(month_ago_idx + 1)]['close_price']
                monthly_change = ((current_price - month_ago_price) / month_ago_price) * 100
            
            return {
                'current_price': float(current_price),
                'daily_change': float(daily_change),
                'weekly_change': float(weekly_change),
                'monthly_change': float(monthly_change),
                'volume': int(current_volume)
            }
            
    except Exception as e:
        print(f"Error calculating metrics for {ticker_symbol}: {str(e)}")
        return None


def sector_summary(request):
    """API endpoint that returns sector-wise summary data"""
    try:
        # Get heatmap data
        response = heatmap_data(request)
        data = json.loads(response.content)
        
        if not data['success']:
            return JsonResponse({'success': False, 'error': 'Failed to get heatmap data'})
        
        sector_summaries = {}
        
        for sector, stocks in data['data'].items():
            if not stocks:
                continue
                
            total_stocks = len(stocks)
            gainers = len([s for s in stocks if s['daily_change'] > 0])
            losers = len([s for s in stocks if s['daily_change'] < 0])
            
            avg_daily_change = sum([s['daily_change'] for s in stocks]) / total_stocks
            avg_weekly_change = sum([s['weekly_change'] for s in stocks]) / total_stocks
            avg_monthly_change = sum([s['monthly_change'] for s in stocks]) / total_stocks
            
            sector_summaries[sector] = {
                'total_stocks': total_stocks,
                'gainers': gainers,
                'losers': losers,
                'avg_daily_change': round(avg_daily_change, 2),
                'avg_weekly_change': round(avg_weekly_change, 2),
                'avg_monthly_change': round(avg_monthly_change, 2),
            }
        
        return JsonResponse({
            'success': True,
            'data': sector_summaries
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })
