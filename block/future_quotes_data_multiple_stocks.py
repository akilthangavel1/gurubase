from fyers_apiv3 import fyersModel
from datetime import datetime, timedelta
import time

client_id = "MMKQTWNJH3-100"
access_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhdWQiOlsiZDoxIiwiZDoyIiwieDowIiwieDoxIiwieDoyIl0sImF0X2hhc2giOiJnQUFBQUFCbjlCUTByeU1udTkyYm91UkJZdXdRUVkxcnhNRDZQUzM1LWVPdEI1MmZ5dGM4bGNiSDB2TFBKeHozdUxDY2lRelB3ODJIM01ETURqU0wxSUdvRUJ6VXB4TjBOVl9CWHhJM29NZERHRkdPV296R21EZz0iLCJkaXNwbGF5X25hbWUiOiIiLCJvbXMiOiJLMSIsImhzbV9rZXkiOiJiZWNjNDQ1ODZmYzdjMjkxYTFmY2EwMGZlYzIwNmJkNDIzYjk4ZWQ0YmFmODI3N2I2YTFiOWNlNiIsImlzRGRwaUVuYWJsZWQiOiJOIiwiaXNNdGZFbmFibGVkIjoiTiIsImZ5X2lkIjoiWUEyOTM5NiIsImFwcFR5cGUiOjEwMCwiZXhwIjoxNzQ0MDcyMjAwLCJpYXQiOjE3NDQwNDkyMDQsImlzcyI6ImFwaS5meWVycy5pbiIsIm5iZiI6MTc0NDA0OTIwNCwic3ViIjoiYWNjZXNzX3Rva2VuIn0.mt4iD5C-n5ICZ6nlTTe1v0uZcUrEHo5eMunLl0juE7w"
    
# Initialize the FyersModel instance with your client_id, access_token, and enable async mode
fyers = fyersModel.FyersModel(client_id=client_id, token=access_token,is_async=False, log_path="")


def date_to_timestamp(date_str, date_format="%d/%m/%Y"):
    dt = datetime.strptime(date_str, date_format)
    return int(time.mktime(dt.timetuple()))

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

from_date = "28/03/2025"
to_date = "07/04/2025"
symbol = "NSE:BAJAJ-AUTO25APRFUT"


print(symbol)
resolution = "1"
client_id = "MMKQTWNJH3-100"
ohlc_daily_data = fetch_ohlc_data(symbol, resolution, from_date, to_date, client_id, access_token)
print(ohlc_daily_data)
