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
    access_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJhcGkuZnllcnMuaW4iLCJpYXQiOjE3Mzg4MzE0NjAsImV4cCI6MTczODg4ODIyMCwibmJmIjoxNzM4ODMxNDYwLCJhdWQiOlsieDowIiwieDoxIiwieDoyIiwiZDoxIiwiZDoyIiwieDoxIiwieDowIl0sInN1YiI6ImFjY2Vzc190b2tlbiIsImF0X2hhc2giOiJnQUFBQUFCbnBIWmtPdGZIXzFyczJpd242c1pEeXVlYzlFVEE3UVNmc3hNWFZKRmtjZ1FLTTdvRHhDMEpOYUtkYkh0LTZ0NndOTEt0TVVTTVUzcXZWaWd3OXB6Zm1vaXVJUjFXRXNadGdZMFhacXBKcTlhWDRvTT0iLCJkaXNwbGF5X25hbWUiOiJBS0lMIFRIQU5HQVZFTCIsIm9tcyI6IksxIiwiaHNtX2tleSI6ImJlY2M0NDU4NmZjN2MyOTFhMWZjYTAwZmVjMjA2YmQ0MjNiOThlZDRiYWY4Mjc3YjZhMWI5Y2U2IiwiaXNEZHBpRW5hYmxlZCI6Ik4iLCJpc010ZkVuYWJsZWQiOiJOIiwiZnlfaWQiOiJZQTI5Mzk2IiwiYXBwVHlwZSI6MTAwLCJwb2FfZmxhZyI6Ik4ifQ.CH-e7oWDEf18R9m8HsQa8Tf5P9y-GkngPgcSn5CW-sg"
    print(access_token)
    access_token = AccessToken.objects.first().value
    print(access_token)
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
    # Use the access token from database
    is_async = False
    fyers.token = access_token
    return fyers

