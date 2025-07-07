from django.core.management.base import BaseCommand
from django.db import connection
from dashboard.models import TickerBase

# Import xalert models to handle foreign key relationships
try:
    from xalert.models import UserStrategySubscription, StrategySignal, StrategyPerformance
    XALERT_AVAILABLE = True
except ImportError:
    XALERT_AVAILABLE = False


class Command(BaseCommand):
    help = 'Delete all TickerBase objects and their associated sub tables'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirm the deletion without prompting',
        )

    def handle(self, *args, **options):
        # Get all ticker symbols before deleting
        tickers = list(TickerBase.objects.all().values_list('ticker_symbol', flat=True))
        
        if not tickers:
            self.stdout.write(
                self.style.WARNING('No TickerBase objects found to delete.')
            )
            return

        self.stdout.write(
            self.style.WARNING(
                f'This will delete {len(tickers)} TickerBase objects and their associated tables:'
            )
        )
        
        for ticker in tickers:
            self.stdout.write(f'  - {ticker}')
            self.stdout.write(f'    - {ticker}_historical_data')
            self.stdout.write(f'    - {ticker}_websocket_data')
            self.stdout.write(f'    - {ticker}_future_historical_data')
            self.stdout.write(f'    - {ticker}_future_websocket_data')
            self.stdout.write(f'    - {ticker}_future_daily_historical_data')
        
        if XALERT_AVAILABLE:
            self.stdout.write(
                self.style.WARNING(
                    '\nThis will also delete related xalert objects:'
                )
            )
            self.stdout.write('  - UserStrategySubscription objects')
            self.stdout.write('  - StrategySignal objects')
            self.stdout.write('  - StrategyPerformance objects')

        # Confirm deletion unless --confirm flag is used
        if not options['confirm']:
            confirm = input('\nAre you sure you want to delete all these objects and tables? [y/N]: ')
            if confirm.lower() != 'y':
                self.stdout.write(
                    self.style.SUCCESS('Operation cancelled.')
                )
                return

        # Delete associated tables first
        self.stdout.write('Deleting associated tables...')
        deleted_tables = []
        failed_tables = []

        with connection.cursor() as cursor:
            for ticker in tickers:
                table_names = [
                    f"{ticker}_historical_data",
                    f"{ticker}_websocket_data", 
                    f"{ticker}_future_historical_data",
                    f"{ticker}_future_websocket_data",
                    f"{ticker}_future_daily_historical_data"
                ]
                
                for table_name in table_names:
                    try:
                        cursor.execute(f'DROP TABLE IF EXISTS "{table_name}" CASCADE')
                        deleted_tables.append(table_name)
                        self.stdout.write(f'  ✓ Deleted table: {table_name}')
                    except Exception as e:
                        failed_tables.append((table_name, str(e)))
                        self.stdout.write(
                            self.style.ERROR(f'  ✗ Failed to delete table {table_name}: {e}')
                        )

        # Delete related objects in xalert app first to avoid foreign key constraints
        if XALERT_AVAILABLE:
            self.stdout.write('\nDeleting related xalert objects...')
            try:
                # Delete UserStrategySubscription objects related to these tickers
                user_subs_deleted = 0
                for ticker in tickers:
                    ticker_obj = TickerBase.objects.filter(ticker_symbol=ticker).first()
                    if ticker_obj:
                        subs_count, _ = UserStrategySubscription.objects.filter(ticker=ticker_obj).delete()
                        user_subs_deleted += subs_count
                        
                        signals_count, _ = StrategySignal.objects.filter(ticker=ticker_obj).delete()
                        perf_count, _ = StrategyPerformance.objects.filter(ticker=ticker_obj).delete()
                        
                        self.stdout.write(f'  ✓ Deleted {subs_count} subscriptions, {signals_count} signals, {perf_count} performance records for {ticker}')
                
                self.stdout.write(
                    self.style.SUCCESS(f'Successfully deleted related xalert objects.')
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error deleting related xalert objects: {e}')
                )

        # Delete TickerBase objects
        self.stdout.write('\nDeleting TickerBase objects...')
        try:
            deleted_count, _ = TickerBase.objects.all().delete()
            self.stdout.write(
                self.style.SUCCESS(f'Successfully deleted {deleted_count} TickerBase objects.')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Failed to delete TickerBase objects: {e}')
            )

        # Summary
        self.stdout.write('\n' + '='*50)
        self.stdout.write('DELETION SUMMARY:')
        self.stdout.write('='*50)
        self.stdout.write(f'Tables deleted: {len(deleted_tables)}')
        self.stdout.write(f'Tables failed: {len(failed_tables)}')
        self.stdout.write(f'TickerBase objects deleted: {deleted_count if "deleted_count" in locals() else 0}')
        
        if failed_tables:
            self.stdout.write('\nFailed tables:')
            for table_name, error in failed_tables:
                self.stdout.write(f'  - {table_name}: {error}')

        self.stdout.write(
            self.style.SUCCESS('\nDeletion process completed.')
        ) 