from fyers_apiv3 import fyersModel
client_id = "MMKQTWNJH3-100"
access_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJhcGkuZnllcnMuaW4iLCJpYXQiOjE3MzkyNTQ5MzAsImV4cCI6MTczOTMyMDIxMCwibmJmIjoxNzM5MjU0OTMwLCJhdWQiOlsieDowIiwieDoxIiwieDoyIiwiZDoxIiwiZDoyIiwieDoxIiwieDowIl0sInN1YiI6ImFjY2Vzc190b2tlbiIsImF0X2hhc2giOiJnQUFBQUFCbnF1eVNFYXBfREd4WVRVelhOT1J6bVlKcE9HRW15U0FyTE9rdVJSRXNxeHBUWEZaTFB4aDl2R2txd1JETE1mbV8tci1HVTF4bDNNZ3Q2T2w0VEczU1VEVmRaU1BVTklRaG1xVVpuYWxkS3NzTlQzTT0iLCJkaXNwbGF5X25hbWUiOiJBS0lMIFRIQU5HQVZFTCIsIm9tcyI6IksxIiwiaHNtX2tleSI6ImJlY2M0NDU4NmZjN2MyOTFhMWZjYTAwZmVjMjA2YmQ0MjNiOThlZDRiYWY4Mjc3YjZhMWI5Y2U2IiwiaXNEZHBpRW5hYmxlZCI6Ik4iLCJpc010ZkVuYWJsZWQiOiJOIiwiZnlfaWQiOiJZQTI5Mzk2IiwiYXBwVHlwZSI6MTAwLCJwb2FfZmxhZyI6Ik4ifQ.Gh2U_p6atOb4-l1GY43bGiuJnTmFBvMAZNlDtDkdtW0"
    
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