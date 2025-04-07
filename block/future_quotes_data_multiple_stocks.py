from fyers_apiv3 import fyersModel
client_id = "MMKQTWNJH3-100"
access_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhdWQiOlsiZDoxIiwiZDoyIiwieDowIiwieDoxIiwieDoyIl0sImF0X2hhc2giOiJnQUFBQUFCbjlCUTByeU1udTkyYm91UkJZdXdRUVkxcnhNRDZQUzM1LWVPdEI1MmZ5dGM4bGNiSDB2TFBKeHozdUxDY2lRelB3ODJIM01ETURqU0wxSUdvRUJ6VXB4TjBOVl9CWHhJM29NZERHRkdPV296R21EZz0iLCJkaXNwbGF5X25hbWUiOiIiLCJvbXMiOiJLMSIsImhzbV9rZXkiOiJiZWNjNDQ1ODZmYzdjMjkxYTFmY2EwMGZlYzIwNmJkNDIzYjk4ZWQ0YmFmODI3N2I2YTFiOWNlNiIsImlzRGRwaUVuYWJsZWQiOiJOIiwiaXNNdGZFbmFibGVkIjoiTiIsImZ5X2lkIjoiWUEyOTM5NiIsImFwcFR5cGUiOjEwMCwiZXhwIjoxNzQ0MDcyMjAwLCJpYXQiOjE3NDQwNDkyMDQsImlzcyI6ImFwaS5meWVycy5pbiIsIm5iZiI6MTc0NDA0OTIwNCwic3ViIjoiYWNjZXNzX3Rva2VuIn0.mt4iD5C-n5ICZ6nlTTe1v0uZcUrEHo5eMunLl0juE7w"
    
# Initialize the FyersModel instance with your client_id, access_token, and enable async mode
fyers = fyersModel.FyersModel(client_id=client_id, token=access_token,is_async=False, log_path="")

data = {
    "symbols":"NSE:SBIN-EQ,NSE:IDEA-EQ"
}

response = fyers.quotes(data=data)
print(response)
symbols = ["NSE:SBIN-EQ", "NSE:RELIANCE-EQ", "NSE:TCS-EQ"] 
# response = get_stock_quotes(symbols)
# print(response)