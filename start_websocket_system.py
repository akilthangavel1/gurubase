#!/usr/bin/env python3
"""
Startup script for the async WebSocket processing system.
This script helps coordinate running both the Celery worker and WebSocket connections.
"""

import subprocess
import sys
import os
import time
import signal
import threading
from pathlib import Path

class WebSocketSystemManager:
    def __init__(self):
        self.celery_process = None
        self.websocket_process = None
        self.running = True
        
    def start_celery_worker(self):
        """Start the Celery worker in the background"""
        print("🚀 Starting Celery worker for WebSocket data processing...")
        
        celery_cmd = [
            sys.executable, 'manage.py', 'celery_worker',
            '--concurrency=4',
            '--loglevel=info'
        ]
        
        try:
            self.celery_process = subprocess.Popen(
                celery_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True
            )
            
            # Give Celery time to start
            time.sleep(3)
            
            if self.celery_process.poll() is None:
                print("✅ Celery worker started successfully")
                return True
            else:
                print("❌ Failed to start Celery worker")
                return False
                
        except Exception as e:
            print(f"❌ Error starting Celery worker: {e}")
            return False
    
    def start_websocket_connections(self, **kwargs):
        """Start the WebSocket connections"""
        print("\n🔗 Starting async WebSocket connections...")
        
        ws_cmd = [
            sys.executable, 'manage.py', 'start_websocket_multi',
            f'--stocks-per-connection={kwargs.get("stocks_per_connection", 50)}',
            f'--max-stocks={kwargs.get("max_stocks", 250)}',
            f'--connection-delay={kwargs.get("connection_delay", 3)}',
            f'--monitor-interval={kwargs.get("monitor_interval", 30)}'
        ]
        
        if kwargs.get('litemode'):
            ws_cmd.append('--litemode')
        
        try:
            self.websocket_process = subprocess.Popen(
                ws_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True
            )
            
            print("✅ WebSocket connections started")
            return True
            
        except Exception as e:
            print(f"❌ Error starting WebSocket connections: {e}")
            return False
    
    def monitor_processes(self):
        """Monitor both processes and show their output"""
        def read_process_output(process, prefix):
            for line in iter(process.stdout.readline, ''):
                if line and self.running:
                    print(f"{prefix}: {line.strip()}")
        
        # Start monitoring threads
        if self.celery_process:
            celery_thread = threading.Thread(
                target=read_process_output, 
                args=(self.celery_process, "🔄 CELERY"),
                daemon=True
            )
            celery_thread.start()
        
        if self.websocket_process:
            ws_thread = threading.Thread(
                target=read_process_output, 
                args=(self.websocket_process, "📡 WEBSOCKET"),
                daemon=True
            )
            ws_thread.start()
        
        try:
            # Wait for processes
            while self.running:
                if self.celery_process and self.celery_process.poll() is not None:
                    print("⚠️  Celery worker has stopped")
                    self.running = False
                    
                if self.websocket_process and self.websocket_process.poll() is not None:
                    print("⚠️  WebSocket connections have stopped")
                    self.running = False
                
                time.sleep(1)
                
        except KeyboardInterrupt:
            self.stop_all()
    
    def stop_all(self):
        """Stop all processes gracefully"""
        print("\n🛑 Stopping all processes...")
        self.running = False
        
        if self.websocket_process:
            try:
                self.websocket_process.terminate()
                self.websocket_process.wait(timeout=10)
                print("✅ WebSocket connections stopped")
            except subprocess.TimeoutExpired:
                self.websocket_process.kill()
                print("🔥 WebSocket connections force-killed")
        
        if self.celery_process:
            try:
                self.celery_process.terminate()
                self.celery_process.wait(timeout=10)
                print("✅ Celery worker stopped")
            except subprocess.TimeoutExpired:
                self.celery_process.kill()
                print("🔥 Celery worker force-killed")
        
        print("🏁 All processes stopped")


def main():
    print("🚀 WebSocket Async Processing System Startup")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not Path('manage.py').exists():
        print("❌ manage.py not found. Please run this script from your Django project root.")
        sys.exit(1)
    
    # Configuration
    config = {
        'stocks_per_connection': 50,
        'max_stocks': 250,
        'connection_delay': 3,
        'monitor_interval': 30,
        'litemode': False
    }
    
    # Parse simple command line args
    if '--help' in sys.argv or '-h' in sys.argv:
        print("""
Usage: python start_websocket_system.py [options]

Options:
  --stocks-per-connection N    Number of stocks per WebSocket connection (default: 50)
  --max-stocks N              Maximum number of stocks to process (default: 250)
  --connection-delay N        Delay between starting connections in seconds (default: 3)
  --monitor-interval N        Monitoring interval in seconds (default: 30)
  --litemode                  Enable lite mode for WebSocket connections
  --help, -h                  Show this help message

Examples:
  python start_websocket_system.py
  python start_websocket_system.py --stocks-per-connection 40 --max-stocks 200
  python start_websocket_system.py --litemode --connection-delay 5
        """)
        sys.exit(0)
    
    # Simple argument parsing
    for i, arg in enumerate(sys.argv[1:], 1):
        if arg == '--litemode':
            config['litemode'] = True
        elif arg.startswith('--stocks-per-connection='):
            config['stocks_per_connection'] = int(arg.split('=')[1])
        elif arg.startswith('--max-stocks='):
            config['max_stocks'] = int(arg.split('=')[1])
        elif arg.startswith('--connection-delay='):
            config['connection_delay'] = int(arg.split('=')[1])
        elif arg.startswith('--monitor-interval='):
            config['monitor_interval'] = int(arg.split('=')[1])
    
    print(f"📋 Configuration:")
    for key, value in config.items():
        print(f"   {key}: {value}")
    print()
    
    # Create system manager
    manager = WebSocketSystemManager()
    
    # Setup signal handler
    def signal_handler(sig, frame):
        manager.stop_all()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Start Celery worker first
        if not manager.start_celery_worker():
            print("❌ Failed to start Celery worker. Exiting.")
            sys.exit(1)
        
        # Start WebSocket connections
        if not manager.start_websocket_connections(**config):
            print("❌ Failed to start WebSocket connections. Stopping Celery and exiting.")
            manager.stop_all()
            sys.exit(1)
        
        print("\n✅ All systems started successfully!")
        print("📊 Monitoring system output...")
        print("⏹️  Press Ctrl+C to stop all processes\n")
        
        # Monitor processes
        manager.monitor_processes()
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        manager.stop_all()
        sys.exit(1)


if __name__ == "__main__":
    main() 