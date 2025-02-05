from fyers_apiv3 import fyersModel
from django.conf import settings
from .models import AccessToken
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
    access_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJhcGkuZnllcnMuaW4iLCJpYXQiOjE3Mzg3NDU0OTQsImV4cCI6MTczODgwMTgzNCwibmJmIjoxNzM4NzQ1NDk0LCJhdWQiOlsieDowIiwieDoxIiwieDoyIiwiZDoxIiwiZDoyIiwieDoxIiwieDowIl0sInN1YiI6ImFjY2Vzc190b2tlbiIsImF0X2hhc2giOiJnQUFBQUFCbm95YVdTWlBUTEV3c2s1cFdwYU43SlZIWmdDSnVvNVlnY2kxZGpkcjJqQ0g0azczTl9pLS1OVWVjWFUzdTF1Nlo4OHd5aGtaZi1aM2RPWWVsQzhXSVpqWnQ2cnlqVXI5b3F6QzR2OGI4QndtT0Vqaz0iLCJkaXNwbGF5X25hbWUiOiJBS0lMIFRIQU5HQVZFTCIsIm9tcyI6IksxIiwiaHNtX2tleSI6ImJlY2M0NDU4NmZjN2MyOTFhMWZjYTAwZmVjMjA2YmQ0MjNiOThlZDRiYWY4Mjc3YjZhMWI5Y2U2IiwiaXNEZHBpRW5hYmxlZCI6Ik4iLCJpc010ZkVuYWJsZWQiOiJOIiwiZnlfaWQiOiJZQTI5Mzk2IiwiYXBwVHlwZSI6MTAwLCJwb2FfZmxhZyI6Ik4ifQ.NWq46KmTbJ8w8Mj_QJQYLg7VIbl92Gz0XUBGUxD_Ac4"
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
    fyers = fyersModel.FyersModel(client_id="MMKQTWNJH3-100", is_async=False, token=access_token, log_path="")
    print(fyers)
    # Use the access token from database
    is_async = False
    fyers.token = access_token
    return fyers

