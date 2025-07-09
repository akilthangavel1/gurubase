from celery import shared_task
from fyers_apiv3 import fyersModel
from django.conf import settings
from .models import TickerBase
import pandas as pd
import time
import requests
from django.db import connection
from fyers_apiv3 import fyersModel
import logging
from datetime import datetime
from .fyers_functions import initialize_fyers   
from dashboard.models import TickerBase, AccessToken
import time

logger = logging.getLogger(__name__)

def symbol_format(symbol):
    return f"NSE:{symbol}-EQ"


@shared_task(queue='websocket_data', bind=True, max_retries=3, default_retry_delay=5)
def process_stock_data(self, message):
    """
    Process incoming websocket data and save to TickerPriceData model
    Optimized for async processing with proper error handling and retries
    """
    try:
        # Handle the actual websocket message format
        if not message:
            logger.warning(f"Empty websocket message: {message}")
            return {"status": "skipped", "reason": "empty_message"}
        
        # Check if it's a data message (type 'sf' for symbol feed)
        if message.get('type') != 'sf':
            logger.debug(f"Skipping non-data message type: {message.get('type', 'unknown')}")
            return {"status": "skipped", "reason": "non_data_message"}
        
        # Extract symbol and price data
        full_symbol = message.get('symbol', '')
        ltp = message.get('ltp')
        
        if not full_symbol or ltp is None:
            logger.warning(f"Missing symbol or ltp in message: {message}")
            return {"status": "error", "reason": "missing_data"}
        
        # Extract base symbol - remove NSE: prefix and FUT suffix
        if full_symbol.startswith('NSE:'):
            base_symbol = full_symbol[4:]  # Remove NSE: prefix
            
        # Remove the futures contract suffix (e.g., 25JULFUT)
        if base_symbol.endswith('25JULFUT'):
            base_symbol = base_symbol[:-8]  # Remove 25JULFUT
        
        # Handle special symbol mappings to match database format
        if base_symbol == 'BAJAJ-AUTO':
            base_symbol = 'BAJAJAUTO'
        elif base_symbol == 'M&M':
            base_symbol = 'MM'
        elif base_symbol == 'M&MFIN':
            base_symbol = 'MMFIN'
        
        base_symbol = base_symbol.lower()
        
        # Check if ticker exists in our database
        try:
            ticker = TickerBase.objects.get(ticker_symbol=base_symbol)
        except TickerBase.DoesNotExist:
            logger.warning(f"Ticker {base_symbol} not found in database")
            return {"status": "error", "reason": "ticker_not_found", "symbol": base_symbol}
        
        # Try to update existing TickerPriceData or create new one
        from dashboard.models import TickerPriceData
        from decimal import Decimal
        
        try:
            # Get or create TickerPriceData for this ticker
            price_data, created = TickerPriceData.objects.get_or_create(
                ticker=ticker,
                defaults={
                    'ltp': Decimal(str(ltp)),
                }
            )
            
            # If it already exists, update the LTP
            if not created:
                price_data.ltp = Decimal(str(ltp))
                price_data.save(update_fields=['ltp', 'last_updated'])
            
            logger.debug(f"Successfully {'created' if created else 'updated'} price data for {base_symbol}: LTP={ltp}")
            
            return {
                "status": "success", 
                "action": "created" if created else "updated",
                "symbol": base_symbol,
                "ltp": float(ltp)
            }
            
        except Exception as db_error:
            logger.error(f"Database error for {base_symbol}: {db_error}")
            
            # Retry the task if it's a temporary database issue
            if self.request.retries < self.max_retries:
                logger.info(f"Retrying task for {base_symbol}, attempt {self.request.retries + 1}")
                raise self.retry(countdown=self.default_retry_delay * (self.request.retries + 1))
            
            # Fallback to old table method if new model fails after retries
            if '25JULFUT' in full_symbol:
                table_name = f"{base_symbol}_future_websocket_data"
            else:
                table_name = f"{base_symbol}_websocket_data"
            
            try:
                insert_query = f"""
                    INSERT INTO "{table_name}" (timestamp, ltp)
                    VALUES (NOW(), %s)
                """
                
                with connection.cursor() as cursor:
                    cursor.execute(insert_query, [float(ltp)])
                    connection.commit()
                
                logger.info(f"Fallback: Successfully inserted websocket data for {base_symbol}: LTP={ltp}")
                return {
                    "status": "success_fallback", 
                    "method": "legacy_table",
                    "symbol": base_symbol,
                    "ltp": float(ltp)
                }
                
            except Exception as fallback_error:
                logger.error(f"Fallback insertion failed for {base_symbol}: {fallback_error}")
                return {
                    "status": "error", 
                    "reason": "all_methods_failed",
                    "symbol": base_symbol,
                    "errors": [str(db_error), str(fallback_error)]
                }
                
    except Exception as e:
        logger.error(f"Error processing websocket message: {e}")
        logger.error(f"Message content: {message}")
        
        # Retry on unexpected errors
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying task due to unexpected error, attempt {self.request.retries + 1}")
            raise self.retry(countdown=self.default_retry_delay * (self.request.retries + 1))
        
        return {
            "status": "error", 
            "reason": "unexpected_error",
            "error": str(e),
            "message": message
        }


@shared_task
def update_historical_data():


    # Get all tickers
    tickers = TickerBase.objects.all()
    
    # Get access token
    try:
        access_token = AccessToken.objects.first().value
        # access_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJhcGkuZnllcnMuaW4iLCJpYXQiOjE3Mzg2MTk0MTUsImV4cCI6MTczODYyOTAxNSwibmJmIjoxNzM4NjE5NDE1LCJhdWQiOlsieDowIiwieDoxIiwieDoyIiwiZDoxIiwiZDoyIiwieDoxIiwieDowIl0sInN1YiI6ImFjY2Vzc190b2tlbiIsImF0X2hhc2giOiJnQUFBQUFCbm9Ub1g2eXppNTkxRXR6UkpSVkhhcURUVEhqb1RWc2tlVXFkX0haenhST3dCdWdQVzJCdEE3WDVINXEyOGlfdUEzS3M1MkFUcWNOY2NFVXY2Z3FEYm9yWV9fZzZDSFl4amNZYmp1cHFfMXhLXzJLOD0iLCJkaXNwbGF5X25hbWUiOiJBS0lMIFRIQU5HQVZFTCIsIm9tcyI6IksxIiwiaHNtX2tleSI6ImJlY2M0NDU4NmZjN2MyOTFhMWZjYTAwZmVjMjA2YmQ0MjNiOThlZDRiYWY4Mjc3YjZhMWI5Y2U2IiwiaXNEZHBpRW5hYmxlZCI6Ik4iLCJpc010ZkVuYWJsZWQiOiJOIiwiZnlfaWQiOiJZQTI5Mzk2IiwiYXBwVHlwZSI6MTAwLCJwb2FfZmxhZyI6Ik4ifQ.mfYyPl7LtrinNooOikwA8ns_53STfkwMInjirlpToWU"

    except:
        print("No access token found")
        return

    # Headers for the API request
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    # fyers = fyersModel.FyersModel(client_id="MMKQTWNJH3-100", is_async=False, token=access_token, log_path="")
    fyers = initialize_fyers()
    for ticker in tickers:
        symbol = f"NSE:{ticker.ticker_symbol.upper()}25JULFUT"
        table_name = f"{ticker.ticker_symbol}_future_historical_data"
        time.sleep(1)
        try:
            data = {
                "symbol": symbol,
                "resolution": "1",
                "range_from": str(int(time.time()) - (1000 * 60)),
                "range_to": str(int(time.time())),
                "date_format":"0",
                "cont_flag":"1"
            }

            response = fyers.history(data=data)
            logger.warning(response)  # For debugging
            # Check if response is already a dict
            if isinstance(response, dict):
                data = response
                # For dict responses, check 's' field for status
                if data.get('s') == 'ok':
                    candles = data.get('candles', [])
                elif data.get('s') == 'no_data':
                    print(f"No data available for {ticker.ticker_symbol}")
                    continue
                else:
                    print(f"Failed to get data for {ticker.ticker_symbol}: {data.get('message', 'Unknown error')}")
                    continue
            else:
                data = response.json()
                if response.status_code == 200 and data.get('status') == 'success':
                    candles = data.get('data', {}).get('candles', [])
                else:
                    print(f"Failed to get data for {ticker.ticker_symbol}: {data.get('message', 'Unknown error')}")
                    continue
            
            # Continue with database insertion if we have candles
            if candles:
                # Insert data into the database
                with connection.cursor() as cursor:
                    # First, add UNIQUE constraint if it doesn't exist
                    try:
                        alter_table_query = f"""
                        ALTER TABLE "{table_name}" 
                        ADD CONSTRAINT {table_name}_datetime_key UNIQUE (datetime);
                        """
                        cursor.execute(alter_table_query)
                        connection.commit()
                    except Exception as e:
                        # Constraint might already exist, that's okay
                        connection.rollback()
                    
                    for candle in candles:
                        timestamp, open_price, high_price, low_price, close_price, volume = candle
                        
                        # Simple INSERT or UPDATE without ON CONFLICT
                        insert_query = f"""
                            INSERT INTO "{table_name}" 
                            (datetime, open_price, high_price, low_price, close_price, volume)
                            VALUES 
                            (to_timestamp(%s), %s, %s, %s, %s, %s)
                            ON CONFLICT (datetime) 
                            DO UPDATE SET 
                                open_price = EXCLUDED.open_price,
                                high_price = EXCLUDED.high_price,
                                low_price = EXCLUDED.low_price,
                                close_price = EXCLUDED.close_price,
                                volume = EXCLUDED.volume;
                        """
                        
                        try:
                            cursor.execute(insert_query, (
                                float(timestamp),
                                float(open_price),
                                float(high_price),
                                float(low_price),
                                float(close_price),
                                int(volume)
                            ))
                            connection.commit()
                            logger.info(f"Successfully inserted/updated data for {ticker.ticker_symbol} at timestamp {timestamp}")
                        except Exception as insert_error:
                            logger.error(f"Error inserting data: {insert_error}")
                            connection.rollback()
                            continue
                print(f"Successfully updated data for {ticker.ticker_symbol}")
            else:
                print(f"No data available for {ticker.ticker_symbol}")

        except Exception as e:
            logger.error(f"Error updating data for {ticker.ticker_symbol}: {str(e)}")
        
        # Sleep to avoid rate limiting
        time.sleep(1) 