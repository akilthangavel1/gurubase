import ssl
import certifi
import websocket
from fyers_apiv3.FyersWebsocket import data_ws
from decouple import config

# Fix SSL Certificate verification error using certifi
ssl_context = ssl.create_default_context(cafile=certifi.where())
websocket._default_ssl_context = ssl_context

# Callback function: On message
def onmessage(message):
    print("Message Received:", message)

# Callback function: On error
def onerror(message):
    print("Error:", message)

# Callback function: On close
def onclose(message):
    print("Connection Closed:", message)

# Callback function: On open/connection
def onopen():
    print("WebSocket Connected. Subscribing to symbols...")
    data_type = "SymbolUpdate"
    symbols = ['NSE:SBIN-EQ', 'NSE:ADANIENT-EQ']
    fyers.subscribe(symbols=symbols, data_type=data_type)
    fyers.keep_running()

# Format access_token: <client_id>:<jwt_token>
client_id = config("FYERS_CLIENT_ID")
jwt_token = config("FYERS_ACCESS_TOKEN")
access_token = f"{client_id}:{jwt_token}"

# Create Fyers WebSocket client
fyers = data_ws.FyersDataSocket(
    access_token=access_token,
    log_path="",
    litemode=True,
    write_to_file=False,
    reconnect=True,
    on_connect=onopen,
    on_close=onclose,
    on_error=onerror,
    on_message=onmessage
)

# Connect to Fyers WebSocket
fyers.connect()
