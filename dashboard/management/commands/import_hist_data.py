from django.core.management.base import BaseCommand
from datetime import datetime, timedelta
from dashboard.models import TickerBase
import time
from dashboard.fyers_functions import get_access_token
from fyers_apiv3 import fyersModel
from django.db import connection
import pandas as pd


def insert_data_into_historical_db(table_name, datetime_value, open_price, high_price, low_price, close_price, volume):
    table_name = table_name.lower()
    print(table_name)
    insert_query = f"""
    INSERT INTO "{table_name}" (datetime, open_price, high_price, low_price, close_price, volume)
    VALUES (%s, %s, %s, %s, %s, %s)
    """
    
    try:
        with connection.cursor() as cursor:
            cursor.execute(insert_query, [datetime_value, open_price, high_price, low_price, close_price, volume])
            print(f"Data inserted successfully into {table_name} table.")
    except Exception as e:
        print(f"Error inserting data into {table_name} table: {e}")


def data_exists(table_name, datetime_value):
    try:
        table_name = table_name.lower()
        query = f"SELECT EXISTS(SELECT 1 FROM {table_name} WHERE datetime = %s)"
        with connection.cursor() as cursor:
            cursor.execute(query, [datetime_value])
            return bool(cursor.fetchone()[0])
    except Exception as e:
        print("An error occurred:", e)
        return False


def future_format_symbol(symbol):
    if symbol == "BAJAJAUTO":
        return "NSE:" + "BAJAJ-AUTO" + "25APRFUT"
    elif symbol == "MM":
        return "NSE:" + "M&M" + "25APRFUT"
    elif symbol == "MMFIN":
        return "NSE:" + "M&MFIN" + "25APRFUT"
    else:
        return "NSE:" + symbol + "25APRFUT"


def date_to_timestamp(date_str, date_format="%d/%m/%Y"):
    dt = datetime.strptime(date_str, date_format)
    return int(time.mktime(dt.timetuple()))


def process_ohlc_data(response):
    if 'candles' not in response:
        return "No candle data found in response."

    candles = response['candles']
    df = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['datetime'] = pd.to_datetime(df['timestamp'], unit='s')
    df = df[['datetime', 'open', 'high', 'low', 'close', 'volume']]
    return df



def fetch_ohlc_data(symbol, resolution, from_date, to_date, client_id, access_token, date_format="%d/%m/%Y"):
    fyers = fyersModel.FyersModel(client_id=client_id, is_async=False, token=access_token, log_path="")
    range_from = date_to_timestamp(from_date, date_format)
    range_to = date_to_timestamp(to_date, date_format) + 24 * 60 * 60 
    data = {
        "symbol": symbol,
        "resolution": resolution,        
        "date_format": "0",              
        "range_from": str(range_from),   
        "range_to": str(range_to),       
        "cont_flag": "1"                 
    }
    try:
        response = fyers.history(data=data)
        if response.get('s') == 'ok':
            return response
        else:
            return f"Error in response: {response}"
        
    except Exception as e:
        return f"An error occurred: {e}"

class Command(BaseCommand):
    help = "Updates historical OHLC data in the database for all tickers."

    def handle(self, *args, **options):
        ticker_details = TickerBase.objects.all()
        
        for ticker in ticker_details:
            try:
                self.stdout.write(self.style.SUCCESS(f"Processing ticker: {ticker.ticker_symbol}"))
                from_date = (datetime.now() - timedelta(days=6)).strftime("%d/%m/%Y")
                # print(from_date)
                # print(type(from_date))
                to_date = (datetime.now() - timedelta(days=1)).strftime("%d/%m/%Y")
                from_date = "28/03/2025"
                to_date = "08/04/2025"
                symbol = future_format_symbol(ticker.ticker_symbol.upper())
                resolution = "1"
                client_id = "MMKQTWNJH3-100"
                access_token = get_access_token()
                print(symbol)
                ohlc_daily_data = fetch_ohlc_data(symbol, resolution, from_date, to_date, client_id, access_token)
                processed_daily_ohlc = process_ohlc_data(ohlc_daily_data)
                time.sleep(1)
                for _, row in processed_daily_ohlc.iterrows():
                    if not data_exists(ticker.ticker_symbol + "_future_historical_data", row.datetime):
                        insert_data_into_historical_db(
                            table_name= ticker.ticker_symbol + "_future_historical_data",
                            datetime_value=row.datetime,
                            open_price=row.open,
                            high_price=row.high,
                            low_price=row.low,
                            close_price=row.close,
                            volume=row.volume
                        )
                        # self.stdout.write(self.style.SUCCESS(f"Inserted data for {ticker.ticker_symbol} on {row.datetime}."))
                    else:
                        # self.stdout.write(self.style.WARNING(f"Data for {ticker.ticker_symbol} on {row.datetime} already exists. Skipping."))
                        pass
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error processing ticker {ticker.ticker_symbol}: {e}"))
                time.sleep(20)
        
        self.stdout.write(self.style.SUCCESS("Data Inserted"))
