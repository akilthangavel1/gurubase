#!/usr/bin/env python
"""
Debug script for WebSocket troubleshooting
Run this to check if everything is set up correctly
"""

import os
import sys
import django

# Add the project directory to Python path
sys.path.append('/Users/akil/Desktop/mg2/gurubase')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gurubase.settings')
django.setup()

def check_prerequisites():
    print("🔍 CHECKING PREREQUISITES...")
    print("=" * 50)
    
    # Check Redis
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, db=0)
        r.ping()
        print("✅ Redis: CONNECTED")
    except Exception as e:
        print(f"❌ Redis: FAILED - {e}")
        print("   Fix: Start Redis with 'brew services start redis' or 'sudo systemctl start redis'")
    
    # Check Celery
    try:
        from celery import Celery
        print("✅ Celery: INSTALLED")
    except Exception as e:
        print(f"❌ Celery: FAILED - {e}")
    
    # Check Fyers API
    try:
        from fyers_apiv3.FyersWebsocket import data_ws
        print("✅ Fyers WebSocket: INSTALLED")
    except Exception as e:
        print(f"❌ Fyers WebSocket: FAILED - {e}")
        print("   Fix: pip install fyers-apiv3")

def check_database():
    print("\n🗄️  CHECKING DATABASE...")
    print("=" * 50)
    
    try:
        from dashboard.models import TickerBase, AccessToken
        
        # Check Access Token
        access_token = AccessToken.objects.first()
        if access_token:
            print(f"✅ Access Token: FOUND ({access_token.value[:20]}...)")
        else:
            print("❌ Access Token: NOT FOUND")
            print("   Fix: Add access token in Django admin: /admin/dashboard/accesstoken/")
        
        # Check Tickers
        ticker_count = TickerBase.objects.count()
        if ticker_count > 0:
            print(f"✅ Tickers: {ticker_count} tickers found")
            
            # Show first few tickers
            first_tickers = list(TickerBase.objects.values_list('ticker_symbol', flat=True)[:5])
            print(f"   Sample tickers: {first_tickers}")
        else:
            print("❌ Tickers: NO TICKERS FOUND")
            print("   Fix: Import tickers with 'python manage.py import_tickers tickerdata.xlsx'")
            
    except Exception as e:
        print(f"❌ Database Error: {e}")

def check_symbol_formatting():
    print("\n🔤 CHECKING SYMBOL FORMATTING...")
    print("=" * 50)
    
    try:
        from dashboard.models import TickerBase
        from dashboard.views import future_format_symbol
        
        sample_tickers = TickerBase.objects.all()[:3]
        
        for ticker in sample_tickers:
            formatted = future_format_symbol(ticker.ticker_symbol.upper())
            print(f"✅ {ticker.ticker_symbol} → {formatted}")
            
    except Exception as e:
        print(f"❌ Symbol Formatting Error: {e}")

def test_celery_task():
    print("\n⚙️  TESTING CELERY TASK...")
    print("=" * 50)
    
    try:
        from dashboard.tasks import process_stock_data
        
        # Create a test message
        test_message = {
            'd': [
                {
                    'symbol': 'NSE:RELIANCE25JULFUT',
                    'ltp': 2500.50
                }
            ]
        }
        
        print("✅ Celery task imported successfully")
        print("   Test message structure:", test_message)
        print("   Note: Run 'celery -A gurubase worker --loglevel=info' in another terminal")
        
    except Exception as e:
        print(f"❌ Celery Task Error: {e}")

def check_tables():
    print("\n📊 CHECKING WEBSOCKET TABLES...")
    print("=" * 50)
    
    try:
        from django.db import connection
        from dashboard.models import TickerBase
        
        with connection.cursor() as cursor:
            sample_ticker = TickerBase.objects.first()
            if sample_ticker:
                tables_to_check = [
                    f"{sample_ticker.ticker_symbol}_websocket_data",
                    f"{sample_ticker.ticker_symbol}_future_websocket_data"
                ]
                
                for table_name in tables_to_check:
                    cursor.execute("""
                        SELECT EXISTS (
                            SELECT 1 FROM information_schema.tables 
                            WHERE table_name = %s
                        )
                    """, [table_name.lower()])
                    
                    if cursor.fetchone()[0]:
                        cursor.execute(f'SELECT COUNT(*) FROM "{table_name}"')
                        count = cursor.fetchone()[0]
                        print(f"✅ {table_name}: EXISTS ({count} records)")
                    else:
                        print(f"❌ {table_name}: NOT FOUND")
                        print(f"   Tables should be created automatically when ticker is saved")
            else:
                print("❌ No tickers found to check tables")
                
    except Exception as e:
        print(f"❌ Table Check Error: {e}")

def main():
    print("🚀 WEBSOCKET DEBUG TOOL")
    print("=" * 50)
    
    check_prerequisites()
    check_database()
    check_symbol_formatting()
    test_celery_task()
    check_tables()
    
    print("\n💡 NEXT STEPS:")
    print("=" * 50)
    print("1. Fix any ❌ issues shown above")
    print("2. Start Celery worker: celery -A gurubase worker --loglevel=info")
    print("3. Run WebSocket: python manage.py start_websocket_multi --max-stocks 10")
    print("4. Check web monitor: http://localhost:8000/websocket-monitor/")

if __name__ == "__main__":
    main() 