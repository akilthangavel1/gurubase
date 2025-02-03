from django.core.management.base import BaseCommand
import pandas as pd
from dashboard.models import TickerBase
import re

class Command(BaseCommand):
    help = 'Import tickers from Excel file'

    def add_arguments(self, parser):
        parser.add_argument('excel_file', type=str, help='Path to the Excel file')

    def clean_ticker_symbol(self, symbol):
        # Remove special characters and convert to uppercase
        clean = re.sub(r'[^a-zA-Z0-9]', '', symbol)
        return clean.upper()

    def handle(self, *args, **kwargs):
        excel_file = kwargs['excel_file']
        success_count = 0
        error_count = 0
        
        try:
            # Read Excel file and display column names
            df = pd.read_excel(excel_file)
            self.stdout.write(f"Columns found in Excel: {list(df.columns)}")
            
            # Process each row individually
            for index, row in df.iterrows():
                try:
                    # Get company name and ticker symbol
                    company_name = str(row.get('Company Name', f'Row {index}')).strip()
                    ticker_symbol = str(row.get('Descr.', '')).strip()  # Using Descr. column for ticker symbol
                    
                    # Clean the ticker symbol
                    ticker_symbol = self.clean_ticker_symbol(ticker_symbol)
                    
                    # Map market cap values
                    market_cap = row['Large/Midcap/Small Cap'].strip()
                    if 'large' in market_cap.lower():
                        market_cap = 'Large Cap'
                    elif 'mid' in market_cap.lower():
                        market_cap = 'Mid Cap'
                    elif 'small' in market_cap.lower():
                        market_cap = 'Small Cap'
                    
                    # Create ticker object
                    ticker = TickerBase(
                        ticker_name=company_name,
                        ticker_symbol=ticker_symbol,
                        ticker_sector=row['Sectors'].strip(),
                        ticker_market_cap=market_cap,
                        ticker_sub_sector=row['Sub - Sector'].strip() if pd.notna(row['Sub - Sector']) else None
                    )
                    
                    # Save without transaction wrapper
                    ticker.save()
                    success_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Successfully imported {company_name} ({ticker_symbol})'
                        )
                    )
                    
                except Exception as e:
                    error_count += 1
                    self.stdout.write(
                        self.style.ERROR(
                            f'Error importing row {index + 2}: {str(e)}'
                        )
                    )
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Import completed: {success_count} successful, {error_count} failed'
                )
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Failed to read Excel file: {str(e)}')
            ) 