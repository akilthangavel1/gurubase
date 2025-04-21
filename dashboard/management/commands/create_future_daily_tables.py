from django.core.management.base import BaseCommand
from django.db import connection
from dashboard.models import TickerBase
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Create future daily historical data tables for all existing tickers'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Creating future daily historical data tables for all tickers...'))
        
        tickers = TickerBase.objects.all()
        count = 0
        
        for ticker in tickers:
            try:
                future_daily_table = f"{ticker.ticker_symbol}_future_daily_historical_data"
                
                create_future_daily_table_query = f"""
                CREATE TABLE IF NOT EXISTS "{future_daily_table}" (
                    id SERIAL PRIMARY KEY,
                    datetime TIMESTAMPTZ NOT NULL,
                    open_price FLOAT NOT NULL,
                    high_price FLOAT NOT NULL,
                    low_price FLOAT NOT NULL,
                    close_price FLOAT NOT NULL,
                    volume BIGINT
                )
                """
                
                with connection.cursor() as cursor:
                    cursor.execute(create_future_daily_table_query)
                
                count += 1
                self.stdout.write(self.style.SUCCESS(f'Created table for {ticker.ticker_symbol}'))
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error creating table for {ticker.ticker_symbol}: {str(e)}'))
                logger.error(f'Error creating table for {ticker.ticker_symbol}: {str(e)}')
        
        self.stdout.write(self.style.SUCCESS(f'Successfully created {count} future daily historical data tables')) 