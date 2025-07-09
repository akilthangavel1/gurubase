from django.core.management.base import BaseCommand
import json
import os
from fyers_apiv3.FyersWebsocket import data_ws
from dashboard.models import AccessToken


class Command(BaseCommand):
    help = 'Start Fyers WebSocket connection and print received data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--symbols',
            nargs='+',
            default=['NSE:SBIN-EQ', 'NSE:ADANIENT-EQ'],  # Using equity symbols as default
            help='List of symbols to subscribe to (default: NSE:SBIN-EQ NSE:ADANIENT-EQ)',
        )
        parser.add_argument(
            '--use-futures',
            action='store_true',
            help='Use futures format for symbols (adds 25JULFUT suffix)',
        )
        parser.add_argument(
            '--litemode',
            action='store_true',
            help='Enable lite mode for WebSocket connection',
        )
        parser.add_argument(
            '--use-config',
            action='store_true',
            help='Use access token from fyers_config.json instead of database',
        )

    def handle(self, *args, **kwargs):
        symbols = kwargs['symbols']
        litemode = kwargs['litemode']
        use_config = kwargs['use_config']
        use_futures = kwargs['use_futures']
        
        # Format symbols for futures if requested
        if use_futures:
            formatted_symbols = []
            for symbol in symbols:
                if symbol.endswith('-EQ'):
                    # Convert NSE:SYMBOL-EQ to NSE:SYMBOL25JULFUT
                    base_symbol = symbol.replace('-EQ', '25JULFUT')
                    formatted_symbols.append(base_symbol)
                else:
                    formatted_symbols.append(symbol)
            symbols = formatted_symbols
        
        self.stdout.write(self.style.SUCCESS(f'Starting Fyers WebSocket to print data'))
        self.stdout.write(f'Symbols: {symbols}')
        self.stdout.write(f'Lite mode: {litemode}')
        self.stdout.write(f'Futures mode: {use_futures}')

        def onmessage(message):
            """
            Callback function to handle incoming messages from the FyersDataSocket WebSocket.

            Parameters:
                message (dict): The received message from the WebSocket.

            """
            self.stdout.write(self.style.SUCCESS("Response:"))
            try:
                print(json.dumps(message, indent=2))
            except Exception as e:
                print(f"Error formatting message: {e}")
                print(f"Raw message: {message}")

        def onerror(message):
            """
            Callback function to handle WebSocket errors.

            Parameters:
                message (dict): The error message received from the WebSocket.

            """
            self.stdout.write(self.style.ERROR("Error:"))
            try:
                # Try to format as JSON if possible
                if isinstance(message, (dict, list)):
                    print(json.dumps(message, indent=2))
                else:
                    print(f"Error message: {message}")
                    print(f"Error type: {type(message)}")
            except Exception as e:
                print(f"Error formatting error message: {e}")
                print(f"Raw error: {message}")

        def onclose(message):
            """
            Callback function to handle WebSocket connection close events.
            """
            self.stdout.write(self.style.WARNING("Connection closed:"))
            try:
                if isinstance(message, (dict, list)):
                    print(json.dumps(message, indent=2))
                else:
                    print(f"Close message: {message}")
            except Exception as e:
                print(f"Error formatting close message: {e}")
                print(f"Raw close message: {message}")

        def onopen():
            """
            Callback function to subscribe to data type and symbols upon WebSocket connection.

            """
            self.stdout.write(self.style.SUCCESS("WebSocket connection opened successfully"))
            
            # Specify the data type and symbols you want to subscribe to
            data_type = "SymbolUpdate"

            self.stdout.write(f"Subscribing to symbols: {symbols}")
            self.stdout.write(f"Data type: {data_type}")
            
            try:
                # Subscribe to the specified symbols and data type
                fyers.subscribe(symbols=symbols, data_type=data_type)
                self.stdout.write(self.style.SUCCESS("Successfully subscribed to symbols"))

                # Keep the socket running to receive real-time data
                fyers.keep_running()
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error subscribing to symbols: {e}"))

        try:
            # Get access token
            if use_config:
                # Try to read from config file
                config_path = os.path.join('block', 'data', 'fyers_config.json')
                if os.path.exists(config_path):
                    with open(config_path, 'r') as f:
                        config = json.load(f)
                        access_token = f"{config['client_id']}:{config['access_token']}"
                        self.stdout.write(self.style.SUCCESS('Using access token from config file'))
                else:
                    self.stdout.write(self.style.ERROR('Config file not found. Using database token.'))
                    use_config = False
            
            if not use_config:
                # Get access token from database
                access_token_obj = AccessToken.objects.first()
                if not access_token_obj:
                    self.stdout.write(self.style.ERROR('No access token found. Please add an access token in Django admin or use --use-config flag.'))
                    return
                access_token = access_token_obj.value
                self.stdout.write(self.style.SUCCESS('Using access token from database'))
            
            self.stdout.write(f'Access token: {access_token[:20]}...')
            
            # Create a FyersDataSocket instance with the provided parameters
            fyers = data_ws.FyersDataSocket(
                access_token=access_token,       # Access token in the format "appid:accesstoken"
                log_path="",                     # Path to save logs. Leave empty to auto-create logs in the current directory.
                litemode=litemode,              # Lite mode disabled. Set to True if you want a lite response.
                write_to_file=False,            # Save response in a log file instead of printing it.
                reconnect=True,                 # Enable auto-reconnection to WebSocket on disconnection.
                on_connect=onopen,              # Callback function to subscribe to data upon connection.
                on_close=onclose,               # Callback function to handle WebSocket connection close events.
                on_error=onerror,               # Callback function to handle WebSocket errors.
                on_message=onmessage            # Callback function to handle incoming messages from the WebSocket.
            )

            self.stdout.write(self.style.SUCCESS('Connecting to Fyers WebSocket...'))
            self.stdout.write(self.style.WARNING('Press Ctrl+C to stop the connection'))
            self.stdout.write('')
            self.stdout.write('Tip: If you get errors, try using equity symbols without --use-futures flag first')
            self.stdout.write('Example: python manage.py print_websocket_data --symbols NSE:SBIN-EQ NSE:RELIANCE-EQ')
            
            # Establish a connection to the Fyers WebSocket
            fyers.connect()
            
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('\nShutting down WebSocket connection...'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error starting WebSocket: {str(e)}')) 