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

logger = logging.getLogger(__name__)

def symbol_format(symbol):
    return f"NSE:{symbol}-EQ"


@shared_task
def update_historical_data():
    from dashboard.models import TickerBase, AccessToken
    import time

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

    for ticker in tickers:
        symbol = f"NSE:{ticker.ticker_symbol.upper()}-EQ"
        table_name = f"{ticker.ticker_symbol}_future_historical_data"
        fyers = fyersModel.FyersModel(client_id="MMKQTWNJH3-100", is_async=False, token=access_token, log_path="")

        try:
           
            data = {
                "symbol": symbol,
                "resolution": "5",
                "range_from": str(int(time.time()) - (500 * 60)),
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