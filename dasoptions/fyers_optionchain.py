from fyers_apiv3 import fyersModel
# from scannerpro.views import get_access_token

client_id = "MMKQTWNJH3-100"
access_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJhcGkuZnllcnMuaW4iLCJpYXQiOjE3Mzk3MDU4MjksImV4cCI6MTczOTc1MjIwOSwibmJmIjoxNzM5NzA1ODI5LCJhdWQiOlsieDowIiwieDoxIiwieDoyIiwiZDoxIiwiZDoyIiwieDoxIiwieDowIl0sInN1YiI6ImFjY2Vzc190b2tlbiIsImF0X2hhc2giOiJnQUFBQUFCbnNjM2x3OTU3blBlZlhOVm9HS1lySUdCaXhBc2t6dk53YjBLX2prNGZnOG9SRXNDRzA2VUZ6Q19oZjdhSVRkYndZcHRsVGM4eFFFSkozNnl2OWlXRFp5V0Noa2NxWEwyYnF2TjRESy01a2lIQ0s0UT0iLCJkaXNwbGF5X25hbWUiOiJBS0lMIFRIQU5HQVZFTCIsIm9tcyI6IksxIiwiaHNtX2tleSI6ImJlY2M0NDU4NmZjN2MyOTFhMWZjYTAwZmVjMjA2YmQ0MjNiOThlZDRiYWY4Mjc3YjZhMWI5Y2U2IiwiaXNEZHBpRW5hYmxlZCI6Ik4iLCJpc010ZkVuYWJsZWQiOiJOIiwiZnlfaWQiOiJZQTI5Mzk2IiwiYXBwVHlwZSI6MTAwLCJwb2FfZmxhZyI6Ik4ifQ.iDltKG83uCUI7yWUh6q9zxa7nFjPzEAaiXcp9CyALzY"


def get_option_chain_data(symbol):
    fyers = fyersModel.FyersModel(client_id=client_id, token=access_token,is_async=False, log_path="")
    data = {
        "symbol":symbol,
        "strikecount":25,
        "timestamp": ""
    }
    response = fyers.optionchain(data=data);
    return response


def get_option_quotes(symbol_quotes):
    fyers = fyersModel.FyersModel(client_id=client_id, token=access_token,is_async=False, log_path="")

    data = {
        "symbols":symbol_quotes
    }

    response = fyers.quotes(data=data)
    return response