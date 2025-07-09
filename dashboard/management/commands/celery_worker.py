from django.core.management.base import BaseCommand
import subprocess
import sys
import os
from django.conf import settings


class Command(BaseCommand):
    help = 'Start Celery worker for processing WebSocket data tasks'

    def add_arguments(self, parser):
        parser.add_argument(
            '--concurrency',
            type=int,
            default=4,
            help='Number of concurrent worker processes (default: 4)',
        )
        parser.add_argument(
            '--loglevel',
            type=str,
            default='info',
            choices=['debug', 'info', 'warning', 'error', 'critical'],
            help='Logging level (default: info)',
        )
        parser.add_argument(
            '--queue',
            type=str,
            default='websocket_data',
            help='Queue name to listen to (default: websocket_data)',
        )

    def handle(self, *args, **kwargs):
        concurrency = kwargs['concurrency']
        loglevel = kwargs['loglevel']
        queue = kwargs['queue']
        
        self.stdout.write(
            self.style.SUCCESS(
                f'🚀 Starting Celery Worker for WebSocket Processing:\n'
                f'   ⚡ Concurrency: {concurrency} processes\n'
                f'   📊 Log level: {loglevel}\n'
                f'   📮 Queue: {queue}\n'
            )
        )

        # Get the project directory
        project_dir = os.path.dirname(settings.BASE_DIR) if hasattr(settings, 'BASE_DIR') else os.getcwd()
        
        # Celery command
        celery_cmd = [
            'celery', 
            '-A', 'gurubase.celery',  # Full path to celery module
            'worker',
            f'--concurrency={concurrency}',
            f'--loglevel={loglevel}',
            f'--queues={queue}',
            '--without-gossip',
            '--without-mingle',
            '--without-heartbeat'
        ]
        
        self.stdout.write(
            self.style.SUCCESS(f'📋 Command: {" ".join(celery_cmd)}')
        )
        
        try:
            # Start Celery worker
            self.stdout.write(
                self.style.SUCCESS(
                    f'🔄 Starting Celery worker...\n'
                    f'   Press Ctrl+C to stop the worker\n'
                )
            )
            
            # Run the Celery worker
            subprocess.run(celery_cmd, cwd=project_dir, check=True)
            
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('\n🛑 Celery worker stopped'))
            
        except subprocess.CalledProcessError as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Celery worker failed: {e}')
            )
            
        except FileNotFoundError:
            self.stdout.write(
                self.style.ERROR(
                    '❌ Celery not found. Install it with: pip install celery\n'
                    '   Or ensure it\'s in your virtual environment'
                )
            ) 