from fyers_apiv3 import fyersModel
from django.conf import settings
from .models import AccessToken
from django.core.exceptions import ObjectDoesNotExist

client_id = settings.FYERS_CONFIG['client_id']

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

def get_stock_quotes(symbol_quotes):
    fyers = initialize_fyers()
    data = {
        "symbols":"NSE:SBIN-EQ,NSE:IDEA-EQ"
    }

    response = fyers.quotes(data=data)
    return response

def initialize_fyers():
    access_token = get_fyers_access_token()
    fyers = fyersModel.FyersModel()
    # Use the access token from database
    is_async = False
    fyers.token = access_token
    return fyers

