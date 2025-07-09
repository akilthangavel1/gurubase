from django.core.management.base import BaseCommand
from fyers_apiv3.FyersWebsocket import data_ws
from dashboard.tasks import process_stock_data
from dashboard.models import TickerBase, AccessToken
from dashboard.views import future_format_symbol


class Command(BaseCommand):
    help = 'Start Fyers WebSocket connection and listen for real-time data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=50,
            help='Limit the number of symbols to subscribe to (default: 50)',
        )
        parser.add_argument(
            '--litemode',
            action='store_true',
            help='Enable lite mode for WebSocket connection',
        )

    def handle(self, *args, **kwargs):
        limit = kwargs['limit']
        litemode = kwargs['litemode']
        
        self.stdout.write(self.style.SUCCESS(f'Starting Fyers WebSocket with limit: {limit}, litemode: {litemode}'))

        def onmessage(message):
            # Display relevant message info - Fyers messages have 'type', 'symbol', 'ltp' structure
            message_type = message.get('type', 'unknown')
            symbol = message.get('symbol', 'N/A')
            ltp = message.get('ltp', 'N/A')
            self.stdout.write(f"Received message: Type={message_type}, Symbol={symbol}, LTP={ltp}")
            
            # Process the data directly instead of using Celery to avoid connection errors
            try:
                process_stock_data(message)
                self.stdout.write(self.style.SUCCESS("Data processed successfully"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error processing data: {e}"))

        def onerror(message):
            self.stdout.write(self.style.ERROR(f"WebSocket Error: {message}"))

        def onclose(message):
            self.stdout.write(self.style.WARNING(f"WebSocket Connection closed: {message}"))
            

        def onopen():
            self.stdout.write(self.style.SUCCESS("WebSocket connection opened successfully"))
            
            data_type = "SymbolUpdate"
            symbols = list(TickerBase.objects.values_list('ticker_symbol', flat=True)[:limit])
            
            self.stdout.write(f"Found {len(symbols)} symbols in database")
            
            # Format symbols for Fyers API
            fyers_symbols = [(future_format_symbol(stock.upper())) for stock in symbols]
            
            self.stdout.write(f"Subscribing to symbols: {fyers_symbols[:5]}...")  # Show first 5
            
            fyers.subscribe(symbols=fyers_symbols, data_type=data_type)
            fyers.keep_running()

        try:
            # Get access token
            access_token_obj = AccessToken.objects.first()
            if not access_token_obj:
                self.stdout.write(self.style.ERROR('No access token found. Please add an access token in Django admin.'))
                return
            
            access_token = access_token_obj.value
            self.stdout.write(self.style.SUCCESS(f'Using access token: {access_token[:20]}...'))
            
            # Initialize Fyers WebSocket
            fyers = data_ws.FyersDataSocket(
                access_token=access_token,
                log_path="",
                litemode=litemode,
                write_to_file=False,
                reconnect=True,
                on_connect=onopen,
                on_close=onclose,
                on_error=onerror,
                on_message=onmessage
            )
            
            self.stdout.write(self.style.SUCCESS('Connecting to Fyers WebSocket...'))
            fyers.connect()
            
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('\nShutting down WebSocket connection...'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error starting WebSocket: {str(e)}')) 