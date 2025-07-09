from django.core.management.base import BaseCommand
from fyers_apiv3.FyersWebsocket import data_ws
from dashboard.tasks import process_stock_data
from dashboard.models import TickerBase, AccessToken
from dashboard.views import future_format_symbol
import threading
import time
from queue import Queue
import signal
import sys
import asyncio
import json
from datetime import datetime
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AsyncWebSocketManager:
    def __init__(self, connection_id, symbols, access_token, litemode=False):
        self.connection_id = connection_id
        self.symbols = symbols
        self.access_token = access_token
        self.litemode = litemode
        self.fyers = None
        self.is_connected = False
        self.message_count = 0
        self.error_count = 0
        self.last_message_time = None
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        self.message_queue = Queue()
        self.stop_flag = threading.Event()
        
    def start_connection(self):
        """Start a single WebSocket connection with async processing"""
        
        def onmessage(message):
            try:
                self.message_count += 1
                self.last_message_time = datetime.now()
                
                # Log message info for monitoring
                message_type = message.get('type', 'unknown')
                symbol = message.get('symbol', 'N/A')
                ltp = message.get('ltp', 'N/A')
                
                logger.info(
                    f"[Connection {self.connection_id}] Message #{self.message_count}: "
                    f"Type={message_type}, Symbol={symbol}, LTP={ltp}"
                )
                
                # Process data asynchronously using Celery
                # This prevents blocking the WebSocket connection
                try:
                    # Use .apply_async() with dedicated queue for WebSocket data
                    task_result = process_stock_data.apply_async(
                        args=[message],
                        queue='websocket_data',
                        retry=True,
                        retry_policy={
                            'max_retries': 3,
                            'interval_start': 1,
                            'interval_step': 1,
                            'interval_max': 10,
                        }
                    )
                    logger.debug(
                        f"[Connection {self.connection_id}] Queued task {task_result.id} "
                        f"for symbol {symbol} to websocket_data queue"
                    )
                except Exception as celery_error:
                    logger.error(
                        f"[Connection {self.connection_id}] Celery task error: {celery_error}"
                    )
                    # Fallback: add to local queue for batch processing
                    self.message_queue.put(message)
                
            except Exception as e:
                self.error_count += 1
                logger.error(
                    f"[Connection {self.connection_id}] Error in onmessage: {e}"
                )

        def onerror(message):
            self.error_count += 1
            logger.error(f"[Connection {self.connection_id}] WebSocket ERROR: {message}")
            self.is_connected = False
            
            # Attempt reconnection if not too many failures
            if self.reconnect_attempts < self.max_reconnect_attempts:
                self._schedule_reconnect()

        def onclose(message):
            logger.warning(f"[Connection {self.connection_id}] WebSocket CLOSED: {message}")
            self.is_connected = False
            
            # Attempt reconnection unless explicitly stopped
            if not self.stop_flag.is_set() and self.reconnect_attempts < self.max_reconnect_attempts:
                self._schedule_reconnect()

        def onopen():
            logger.info(
                f"[Connection {self.connection_id}] WebSocket CONNECTED: "
                f"Subscribing to {len(self.symbols)} symbols"
            )
            logger.info(
                f"[Connection {self.connection_id}] Sample symbols: "
                f"{self.symbols[:3]}... (showing first 3)"
            )
            
            try:
                data_type = "SymbolUpdate"
                self.fyers.subscribe(symbols=self.symbols, data_type=data_type)
                self.is_connected = True
                self.reconnect_attempts = 0  # Reset on successful connection
                
                # Start keep running in a separate thread to prevent blocking
                threading.Thread(
                    target=self._keep_running,
                    name=f"KeepRunning-{self.connection_id}",
                    daemon=True
                ).start()
                
            except Exception as subscribe_error:
                logger.error(
                    f"[Connection {self.connection_id}] Subscription error: {subscribe_error}"
                )
                self.is_connected = False

        try:
            # Initialize Fyers WebSocket with better error handling
            self.fyers = data_ws.FyersDataSocket(
                access_token=self.access_token,
                log_path="",
                litemode=self.litemode,
                write_to_file=False,
                reconnect=True,
                on_connect=onopen,
                on_close=onclose,
                on_error=onerror,
                on_message=onmessage
            )
            
            logger.info(f"[Connection {self.connection_id}] Starting WebSocket connection...")
            self.fyers.connect()
            
        except Exception as e:
            logger.error(f"[Connection {self.connection_id}] Error starting WebSocket: {str(e)}")
            self.is_connected = False
            self._schedule_reconnect()

    def _keep_running(self):
        """Keep the WebSocket running in a separate thread"""
        try:
            if self.fyers:
                self.fyers.keep_running()
        except Exception as e:
            logger.error(f"[Connection {self.connection_id}] Keep running error: {e}")
            self.is_connected = False

    def _schedule_reconnect(self):
        """Schedule a reconnection attempt"""
        if self.stop_flag.is_set():
            return
            
        self.reconnect_attempts += 1
        delay = min(30, 5 * self.reconnect_attempts)  # Max 30 seconds delay
        
        logger.info(
            f"[Connection {self.connection_id}] Scheduling reconnect attempt "
            f"{self.reconnect_attempts}/{self.max_reconnect_attempts} in {delay}s"
        )
        
        def reconnect():
            time.sleep(delay)
            if not self.stop_flag.is_set():
                logger.info(f"[Connection {self.connection_id}] Attempting reconnection...")
                self.start_connection()
        
        threading.Thread(target=reconnect, daemon=True).start()

    def stop(self):
        """Gracefully stop the WebSocket connection"""
        self.stop_flag.set()
        if self.fyers:
            try:
                self.fyers.close()
                logger.info(f"[Connection {self.connection_id}] Connection closed gracefully")
            except Exception as e:
                logger.error(f"[Connection {self.connection_id}] Error closing connection: {e}")

    def get_stats(self):
        """Get connection statistics"""
        return {
            'connection_id': self.connection_id,
            'is_connected': self.is_connected,
            'message_count': self.message_count,
            'error_count': self.error_count,
            'symbol_count': len(self.symbols),
            'last_message_time': self.last_message_time,
            'reconnect_attempts': self.reconnect_attempts
        }


class Command(BaseCommand):
    help = 'Start multiple async Fyers WebSocket connections with Celery processing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--stocks-per-connection',
            type=int,
            default=50,
            help='Number of stocks per WebSocket connection (default: 50)',
        )
        parser.add_argument(
            '--max-stocks',
            type=int,
            default=250,
            help='Maximum number of stocks to process (default: 250)',
        )
        parser.add_argument(
            '--litemode',
            action='store_true',
            help='Enable lite mode for WebSocket connections',
        )
        parser.add_argument(
            '--connection-delay',
            type=int,
            default=3,
            help='Delay in seconds between starting connections (default: 3)',
        )
        parser.add_argument(
            '--monitor-interval',
            type=int,
            default=30,
            help='Monitoring interval in seconds (default: 30)',
        )

    def handle(self, *args, **kwargs):
        stocks_per_connection = kwargs['stocks_per_connection']
        max_stocks = kwargs['max_stocks']
        litemode = kwargs['litemode']
        connection_delay = kwargs['connection_delay']
        monitor_interval = kwargs['monitor_interval']
        
        self.stdout.write(
            self.style.SUCCESS(
                f'🚀 Starting Async Multi-WebSocket Manager:\n'
                f'   📊 Stocks per connection: {stocks_per_connection}\n'
                f'   📈 Max stocks: {max_stocks}\n'
                f'   🔧 Lite mode: {litemode}\n'
                f'   ⏱️  Connection delay: {connection_delay}s\n'
                f'   📡 Monitor interval: {monitor_interval}s'
            )
        )

        # Get access token
        try:
            access_token_obj = AccessToken.objects.first()
            if not access_token_obj:
                self.stdout.write(
                    self.style.ERROR('❌ No access token found. Please add an access token in Django admin.')
                )
                return
            
            access_token = access_token_obj.value
            self.stdout.write(
                self.style.SUCCESS(f'🔑 Using access token: {access_token[:20]}...')
            )
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error getting access token: {str(e)}'))
            return

        # Get all ticker symbols
        try:
            all_symbols = list(TickerBase.objects.values_list('ticker_symbol', flat=True)[:max_stocks])
            self.stdout.write(self.style.SUCCESS(f"📋 Found {len(all_symbols)} symbols in database"))
            
            if not all_symbols:
                self.stdout.write(self.style.ERROR('❌ No ticker symbols found in database'))
                return
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error getting ticker symbols: {str(e)}'))
            return

        # Format symbols for Fyers API
        fyers_symbols = [future_format_symbol(stock.upper()) for stock in all_symbols]
        
        # Split symbols into chunks for multiple connections
        symbol_chunks = [
            fyers_symbols[i:i + stocks_per_connection] 
            for i in range(0, len(fyers_symbols), stocks_per_connection)
        ]
        
        num_connections = len(symbol_chunks)
        self.stdout.write(
            self.style.SUCCESS(
                f'🔗 Creating {num_connections} async WebSocket connections:\n'
                f'   📊 Total symbols: {len(fyers_symbols)}\n'
                f'   🔢 Symbols per connection: {stocks_per_connection}\n'
                f'   🎯 Processing via Celery tasks'
            )
        )

        # Create WebSocket managers
        managers = []
        
        # Setup signal handler for graceful shutdown
        def signal_handler(sig, frame):
            self.stdout.write(self.style.WARNING('\n🛑 Shutting down all WebSocket connections...'))
            for manager in managers:
                manager.stop()
            time.sleep(2)  # Give time for graceful shutdown
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Start connections
        try:
            for i, symbols_chunk in enumerate(symbol_chunks, 1):
                self.stdout.write(
                    f"🔌 Starting connection {i}/{num_connections} with {len(symbols_chunk)} symbols..."
                )
                
                manager = AsyncWebSocketManager(
                    connection_id=i,
                    symbols=symbols_chunk,
                    access_token=access_token,
                    litemode=litemode
                )
                managers.append(manager)
                
                # Start connection in a separate thread
                thread = threading.Thread(
                    target=manager.start_connection,
                    name=f"AsyncWebSocket-{i}",
                    daemon=True
                )
                thread.start()
                
                # Delay between connections to avoid overwhelming the API
                if i < num_connections:
                    time.sleep(connection_delay)
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'\n✅ All {num_connections} async WebSocket connections started!\n'
                    f'   📈 Processing {len(fyers_symbols)} symbols\n'
                    f'   🔄 Data processed via Celery tasks\n'
                    f'   ⏹️  Press Ctrl+C to stop all connections\n'
                )
            )
            
            # Monitor connections
            self.monitor_connections(managers, monitor_interval)
            
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('\n🛑 Shutting down all connections...'))
            for manager in managers:
                manager.stop()
                        
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error starting connections: {str(e)}'))

    def monitor_connections(self, managers, monitor_interval):
        """Enhanced monitoring with detailed connection statistics"""
        try:
            while True:
                time.sleep(monitor_interval)
                
                # Gather statistics
                stats = [manager.get_stats() for manager in managers]
                connected_count = sum(1 for s in stats if s['is_connected'])
                total_messages = sum(s['message_count'] for s in stats)
                total_errors = sum(s['error_count'] for s in stats)
                
                # Display comprehensive status
                self.stdout.write(
                    f"\n📊 ASYNC CONNECTION STATUS [{datetime.now().strftime('%H:%M:%S')}]:\n"
                    f"   🟢 Connected: {connected_count}/{len(managers)} connections\n"
                    f"   📨 Total messages: {total_messages:,}\n"
                    f"   ❌ Total errors: {total_errors}\n"
                    f"   🔄 Processing: Async via Celery\n"
                )
                
                # Show individual connection details
                for stat in stats:
                    status_icon = "🟢" if stat['is_connected'] else "🔴"
                    last_msg = stat['last_message_time']
                    last_msg_str = last_msg.strftime('%H:%M:%S') if last_msg else 'Never'
                    
                    self.stdout.write(
                        f"   Connection {stat['connection_id']}: {status_icon} "
                        f"({stat['message_count']:,} msgs, {stat['error_count']} errs, "
                        f"{stat['symbol_count']} symbols, last: {last_msg_str})"
                    )
                    
                    if stat['reconnect_attempts'] > 0:
                        self.stdout.write(
                            f"      🔄 Reconnect attempts: {stat['reconnect_attempts']}"
                        )
                
                self.stdout.write("─" * 80)
                
        except KeyboardInterrupt:
            pass 