from fyers_apiv3 import fyersModel
from django.conf import settings

client_id = settings.FYERS_CONFIG['client_id']
access_token = ""

def get_stock_quotes(symbol_quotes):
    fyers = fyersModel.FyersModel(client_id=client_id, token=access_token,is_async=False, log_path="")

    data = {
        "symbols":"NSE:SBIN-EQ,NSE:IDEA-EQ"
    }

    response = fyers.quotes(data=data)
    return response