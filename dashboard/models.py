from django.db import models, connection
import re
from django.core.exceptions import ValidationError

class TickerBase(models.Model):
    LARGE_CAP = 'Large Cap'
    MID_CAP = 'Mid Cap'
    SMALL_CAP = 'Small Cap'

    MARKET_CAP_CHOICES = [
        (LARGE_CAP, 'Large Cap'),
        (MID_CAP, 'Mid Cap'),
        (SMALL_CAP, 'Small Cap'),
    ]
    AUTOMOBILE = 'Automobile'
    BANKING = 'Banking'
    CAPITAL_GOODS = 'Capital Goods'
    CEMENT = 'Cement'
    CHEMICALS = 'Chemicals'
    FINANCE = 'Finance'
    FMCG = 'FMCG'
    INDEX = 'Index'
    INFRASTRUCTURE = 'Infrastructure'
    MEDIA = 'Media'
    METALS = 'Metals'
    OIL_AND_GAS = 'Oil and Gas'
    PHARMA = 'Pharma'
    POWER = 'Power'
    REALTY = 'Realty'
    TECHNOLOGY = 'Technology'
    TELECOM = 'Telecom'
    TEXTILE = 'Textile'
    OTHERS = 'Others'

    SECTOR_CHOICES = [
        (AUTOMOBILE, 'Automobile'),
        (BANKING, 'Banking'),
        (CAPITAL_GOODS, 'Capital Goods'),
        (CEMENT, 'Cement'),
        (CHEMICALS, 'Chemicals'),
        (FINANCE, 'Finance'),
        (FMCG, 'FMCG'),
        (INDEX, 'Index'),
        (INFRASTRUCTURE, 'Infrastructure'),
        (MEDIA, 'Media'),
        (METALS, 'Metals'),
        (OIL_AND_GAS, 'Oil and Gas'),
        (PHARMA, 'Pharma'),
        (POWER, 'Power'),
        (REALTY, 'Realty'),
        (TECHNOLOGY, 'Technology'),
        (TELECOM, 'Telecom'),
        (TEXTILE, 'Textile'),
        (OTHERS, 'Others'),
    ]

    ticker_name = models.CharField(max_length=200, unique=True)
    ticker_symbol = models.CharField(max_length=20, unique=True)
    ticker_sector = models.CharField(
        max_length=50,
        choices=SECTOR_CHOICES,
        default=OTHERS,
    )
    ticker_sub_sector = models.CharField(max_length=100, blank=True, null=True)
    ticker_market_cap = models.CharField(
        max_length=20,
        choices=MARKET_CAP_CHOICES,
        default=LARGE_CAP,
    )
    
    def __str__(self):
        return f"{self.ticker_symbol.upper()} ({self.ticker_name})"

    def save(self, *args, **kwargs):
        """
        Override save to validate ticker_symbol and create five associated tables:
        1. `<ticker_symbol>_historical_data` - Historical OHLC data table
        2. `<ticker_symbol>_websocket_data` - Real-time WebSocket data table
        3. `<ticker_symbol>_future_historical_data` - Futures historical OHLC data table
        4. `<ticker_symbol>_future_websocket_data` - Futures real-time WebSocket data table
        5. `<ticker_symbol>_future_daily_historical_data` - Futures daily historical OHLC data table
        """
        # Validate ticker_symbol
        if not re.match(r'^[a-zA-Z0-9_]+$', self.ticker_symbol):
            raise ValidationError("Ticker symbol contains invalid characters. Only alphanumeric and underscores are allowed.")

        # Ensure ticker_symbol is lowercase for consistency
        self.ticker_symbol = self.ticker_symbol.lower()

        # Save the TickerBase instance
        super().save(*args, **kwargs)

        # Define descriptive table names
        base_table = f"{self.ticker_symbol}_historical_data"
        wc_table = f"{self.ticker_symbol}_websocket_data"
        future_table = f"{self.ticker_symbol}_future_historical_data"
        future_wc_table = f"{self.ticker_symbol}_future_websocket_data"
        future_daily_table = f"{self.ticker_symbol}_future_daily_historical_data"

        # SQL queries to create the tables
        create_base_table_query = f"""
        CREATE TABLE IF NOT EXISTS "{base_table}" (
            id SERIAL PRIMARY KEY,
            datetime TIMESTAMPTZ NOT NULL,
            open_price FLOAT NOT NULL,
            high_price FLOAT NOT NULL,
            low_price FLOAT NOT NULL,
            close_price FLOAT NOT NULL,
            volume BIGINT
        )
        """
        create_wc_table_query = f"""
        CREATE TABLE IF NOT EXISTS "{wc_table}" (
            id SERIAL PRIMARY KEY,
            timestamp TIMESTAMPTZ NOT NULL,
            ltp FLOAT NOT NULL
        )
        """
        create_future_table_query = f"""
        CREATE TABLE IF NOT EXISTS "{future_table}" (
            id SERIAL PRIMARY KEY,
            datetime TIMESTAMPTZ NOT NULL,
            open_price FLOAT NOT NULL,
            high_price FLOAT NOT NULL,
            low_price FLOAT NOT NULL,
            close_price FLOAT NOT NULL,
            volume BIGINT
        )
        """
        create_future_wc_table_query = f"""
        CREATE TABLE IF NOT EXISTS "{future_wc_table}" (
            id SERIAL PRIMARY KEY,
            timestamp TIMESTAMPTZ NOT NULL,
            ltp FLOAT NOT NULL
        )
        """
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

        # Execute the queries to create tables
        try:
            with connection.cursor() as cursor:
                cursor.execute(create_base_table_query)
                cursor.execute(create_wc_table_query)
                cursor.execute(create_future_table_query)
                cursor.execute(create_future_wc_table_query)
                cursor.execute(create_future_daily_table_query)
        except Exception as e:
            raise ValidationError(f"Error creating tables for {self.ticker_symbol}: {str(e)}")



from django.db import models
from django.core.exceptions import ValidationError

class AccessToken(models.Model):
    value = models.TextField()

    def save(self, *args, **kwargs):
        if not self.pk and AccessToken.objects.exists():
            raise ValidationError('Only one instance of SingleRecord is allowed.')
        return super(AccessToken, self).save(*args, **kwargs)

    def __str__(self):
        return self.value

class TickerPriceData(models.Model):
    """Model for real-time ticker price data"""
    ticker = models.ForeignKey(TickerBase, on_delete=models.CASCADE, related_name='price_data')
    ltp = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Last Traded Price")
    daily_change_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    daily_change_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    weekly_change_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    weekly_change_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    previous_day_close = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    previous_week_close = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'dashboard_tickerpricedata'  # Use existing table
        verbose_name = 'Ticker Price Data'
        verbose_name_plural = 'Ticker Price Data'
        ordering = ['-last_updated']
    
    def __str__(self):
        return f"{self.ticker.ticker_symbol} - ₹{self.ltp} ({self.daily_change_percentage:+.2f}%)"