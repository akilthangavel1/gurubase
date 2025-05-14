import pandas as pd
from fyers_apiv3 import fyersModel
from datetime import datetime, timedelta
import time

client_id = "MMKQTWNJH3-100"
access_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhdWQiOlsiZDoxIiwiZDoyIiwieDowIiwieDoxIiwieDoyIl0sImF0X2hhc2giOiJnQUFBQUFCb0g2Z2VvZWlCZXp6SEJHdUUyR3dTRXRZV1RSb09qaUxOck9wQWVLcHpTbWFPakwxME9EMnduQ0JaY3ZPS1VhMXVhNm12a3I4VF82czZiOWRGZzJnYWhyai1YRHktbE5paHZXMTFRTFdsTzE4Y2h3ST0iLCJkaXNwbGF5X25hbWUiOiIiLCJvbXMiOiJLMSIsImhzbV9rZXkiOiJiZWNjNDQ1ODZmYzdjMjkxYTFmY2EwMGZlYzIwNmJkNDIzYjk4ZWQ0YmFmODI3N2I2YTFiOWNlNiIsImlzRGRwaUVuYWJsZWQiOiJOIiwiaXNNdGZFbmFibGVkIjoiTiIsImZ5X2lkIjoiWUEyOTM5NiIsImFwcFR5cGUiOjEwMCwiZXhwIjoxNzQ3MDA5ODAwLCJpYXQiOjE3NDY5MDUxMTgsImlzcyI6ImFwaS5meWVycy5pbiIsIm5iZiI6MTc0NjkwNTExOCwic3ViIjoiYWNjZXNzX3Rva2VuIn0.lSQZvuNn_incPSTQy51brq02clWcHWxxPBFKyRDRxyw"


# Initialize Fyers API
fyers = fyersModel.FyersModel(client_id=client_id, token=access_token, is_async=False, log_path="")

# Define the stock symbols
symbols = {
    "ONGC": "NSE:ONGC-EQ",
    "IOC": "NSE:IOC-EQ"
}

# Date range for last 7 days
to_date = datetime.now()
from_date = to_date - timedelta(days=2)

# Convert to UNIX timestamp format
to_ts = int(time.mktime(to_date.timetuple()))
from_ts = int(time.mktime(from_date.timetuple()))

def fetch_5min_data(symbol):
    try:
        print(f"Fetching data for symbol: {symbol}")
        data = {
            "symbol": symbol,
            "resolution": "5",  # 5-minute interval
            "date_format": "1",  # date format (1 is for 'YYYY-MM-DD')
            "range_from": from_date.strftime('%Y-%m-%d'),
            "range_to": to_date.strftime('%Y-%m-%d'),
            "cont_flag": "1"  # Continuous flag to allow historical data
        }
        print(f"Request data: {data}")
        response = fyers.history(data=data)
        print("!!!!!!!!!!!!!!!!!!!!")
        print(f"Response: {response}")
        if response.get('s') == 'ok':
            df = pd.DataFrame(response["candles"], columns=["timestamp", "open", "high", "low", "close", "volume"])
            df["datetime"] = pd.to_datetime(df["timestamp"], unit='s')
            df.set_index("datetime", inplace=True)
            df.drop("timestamp", axis=1, inplace=True)
            return df
        else:
            print(f"Error in response for {symbol}: {response}")
            return None
    except Exception as e:
        print(f"Error fetching data for {symbol}: {e}")
        return None

# Fetch 5-minute data for ONGC and IOC
ongc_df = fetch_5min_data(symbols["ONGC"])
ioc_df = fetch_5min_data(symbols["IOC"])

# Save the data to CSV files
if ongc_df is not None:
    ongc_df.to_csv("ONGC_Fyers_5min.csv")
if ioc_df is not None:
    ioc_df.to_csv("IOC_Fyers_5min.csv")

print("Data saved as CSV files.")
