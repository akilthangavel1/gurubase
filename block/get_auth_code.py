

# Import the required module from the fyers_apiv3 package
from fyers_apiv3 import fyersModel

# Define your Fyers API credentials
client_id = "MMKQTWNJH3-100"# Replace with your client ID
secret_key =  "EUT312TGNM"
redirect_uri = "https://trade.fyers.in/api-login/redirect-uri/index.html"# Replace with your redirect URI
response_type = "code" 
state = "sample_state"


# Create a session model with the provided credentials
session = fyersModel.SessionModel(
    client_id=client_id,
    secret_key=secret_key,
    redirect_uri=redirect_uri,
    response_type=response_type
)

# Generate the auth code using the session model
response = session.generate_authcode()

# Print the auth code received in the response
print(response)

