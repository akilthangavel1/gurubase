from fyers_apiv3 import fyersModel
client_id = "MMKQTWNJH3-100"
access_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJhcGkuZnllcnMuaW4iLCJpYXQiOjE3Mzg2MTk0MTUsImV4cCI6MTczODYyOTAxNSwibmJmIjoxNzM4NjE5NDE1LCJhdWQiOlsieDowIiwieDoxIiwieDoyIiwiZDoxIiwiZDoyIiwieDoxIiwieDowIl0sInN1YiI6ImFjY2Vzc190b2tlbiIsImF0X2hhc2giOiJnQUFBQUFCbm9Ub1g2eXppNTkxRXR6UkpSVkhhcURUVEhqb1RWc2tlVXFkX0haenhST3dCdWdQVzJCdEE3WDVINXEyOGlfdUEzS3M1MkFUcWNOY2NFVXY2Z3FEYm9yWV9fZzZDSFl4amNZYmp1cHFfMXhLXzJLOD0iLCJkaXNwbGF5X25hbWUiOiJBS0lMIFRIQU5HQVZFTCIsIm9tcyI6IksxIiwiaHNtX2tleSI6ImJlY2M0NDU4NmZjN2MyOTFhMWZjYTAwZmVjMjA2YmQ0MjNiOThlZDRiYWY4Mjc3YjZhMWI5Y2U2IiwiaXNEZHBpRW5hYmxlZCI6Ik4iLCJpc010ZkVuYWJsZWQiOiJOIiwiZnlfaWQiOiJZQTI5Mzk2IiwiYXBwVHlwZSI6MTAwLCJwb2FfZmxhZyI6Ik4ifQ.mfYyPl7LtrinNooOikwA8ns_53STfkwMInjirlpToWU"

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