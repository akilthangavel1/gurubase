from fyers_apiv3 import fyersModel
from django.conf import settings
from .models import AccessToken, TickerBase
from django.core.exceptions import ObjectDoesNotExist



def get_access_token():
    try:
        # Get the first (and only) access token from the model
        token_obj = AccessToken.objects.first()
        if token_obj:
            return token_obj.value
        return None
    except ObjectDoesNotExist:
        return None

# Replace the static access_token with a function call
def get_fyers_access_token():
    access_token = get_access_token()
    if not access_token:
        raise ValueError("No access token found in database")
    return access_token

def initialize_fyers():
    access_token = get_fyers_access_token()
    fyers = fyersModel.FyersModel(client_id="MMKQTWNJH3-100", is_async=False, token=access_token, log_path="")
    # Use the access token from database
    is_async = False
    fyers.token = access_token
    return fyers

def get_live_data():
    fyers = initialize_fyers()
    tickers = TickerBase.objects.all()
    # Create comma-separated string of symbols in required format
    symbols = ','.join([f"NSE:{ticker.ticker_symbol.upper()}25MARFUT" for ticker in tickers])
    data = {
        "symbols": symbols
    }
    data = fyers.quotes(data)
    return data