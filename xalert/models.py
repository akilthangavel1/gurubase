from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from dashboard.models import TickerBase

class Strategy(models.Model):
    """Pre-defined trading strategies with their parameters"""
    STRATEGY_TYPES = [
        ('MA_CROSSOVER', 'Moving Average Crossover'),
        ('MA_BREAKOUT', 'Moving Average Breakout'),
        ('MA_SUPPORT', 'Moving Average Support'),
    ]
    
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField()
    strategy_type = models.CharField(max_length=20, choices=STRATEGY_TYPES)
    
    # Strategy parameters (stored as JSON-like fields for flexibility)
    short_period = models.IntegerField(help_text="Short moving average period")
    long_period = models.IntegerField(help_text="Long moving average period")
    
    # Additional strategy parameters
    min_volume = models.BigIntegerField(null=True, blank=True, help_text="Minimum volume requirement")
    min_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Minimum price requirement")
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['name']
        verbose_name_plural = "Strategies"
    
    def __str__(self):
        return f"{self.name} (MA{self.short_period}/{self.long_period})"

class UserStrategySubscription(models.Model):
    """Users subscribe to strategies to receive alerts"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='strategy_subscriptions')
    strategy = models.ForeignKey(Strategy, on_delete=models.CASCADE, related_name='subscribers')
    ticker = models.ForeignKey(TickerBase, on_delete=models.CASCADE, null=True, blank=True, 
                               help_text="If specified, only get alerts for this ticker")
    
    # Subscription settings
    is_active = models.BooleanField(default=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)
    last_alert_sent = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ['user', 'strategy', 'ticker']
        ordering = ['-subscribed_at']
    
    def __str__(self):
        ticker_info = f" for {self.ticker.ticker_symbol}" if self.ticker else " (All Tickers)"
        return f"{self.user.username} - {self.strategy.name}{ticker_info}"

class StrategySignal(models.Model):
    """Generated signals when strategies trigger on tickers"""
    SIGNAL_TYPES = [
        ('BUY', 'Buy Signal'),
        ('SELL', 'Sell Signal'),
        ('NEUTRAL', 'Neutral'),
    ]
    
    strategy = models.ForeignKey(Strategy, on_delete=models.CASCADE, related_name='signals')
    ticker = models.ForeignKey(TickerBase, on_delete=models.CASCADE)
    
    signal_type = models.CharField(max_length=10, choices=SIGNAL_TYPES)
    trigger_price = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Moving average values at the time of signal
    short_ma_value = models.DecimalField(max_digits=10, decimal_places=2)
    long_ma_value = models.DecimalField(max_digits=10, decimal_places=2)
    volume = models.BigIntegerField(null=True, blank=True)
    
    # Signal metadata
    signal_strength = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, 
                                          help_text="Signal strength or confidence score")
    triggered_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        ordering = ['-triggered_at']
        unique_together = ['strategy', 'ticker', 'triggered_at']
    
    def __str__(self):
        return f"{self.strategy.name} - {self.ticker.ticker_symbol} - {self.signal_type} at ₹{self.trigger_price}"

class UserAlert(models.Model):
    """Personal alerts sent to users based on their strategy subscriptions"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='alerts')
    subscription = models.ForeignKey(UserStrategySubscription, on_delete=models.CASCADE, related_name='alerts')
    signal = models.ForeignKey(StrategySignal, on_delete=models.CASCADE, related_name='user_alerts')
    
    # Alert details
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    sent_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    
    # Notification settings
    email_sent = models.BooleanField(default=False)
    sms_sent = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-sent_at']
    
    def __str__(self):
        return f"Alert for {self.user.username} - {self.signal.strategy.name} - {self.signal.ticker.ticker_symbol}"
    
    def mark_as_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save()

class StrategyPerformance(models.Model):
    """Track strategy performance metrics"""
    strategy = models.ForeignKey(Strategy, on_delete=models.CASCADE, related_name='performance')
    ticker = models.ForeignKey(TickerBase, on_delete=models.CASCADE, null=True, blank=True)
    
    # Performance metrics
    total_signals = models.IntegerField(default=0)
    buy_signals = models.IntegerField(default=0)
    sell_signals = models.IntegerField(default=0)
    
    # Success rate (if we track trades)
    successful_signals = models.IntegerField(default=0)
    success_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    
    # Date range for this performance data
    period_start = models.DateTimeField()
    period_end = models.DateTimeField()
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['strategy', 'ticker', 'period_start', 'period_end']
        ordering = ['-last_updated']
    
    def __str__(self):
        ticker_info = f" - {self.ticker.ticker_symbol}" if self.ticker else " - All Tickers"
        return f"{self.strategy.name}{ticker_info} Performance"
