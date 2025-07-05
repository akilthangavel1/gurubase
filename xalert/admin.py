from django.contrib import admin
from .models import Strategy, UserStrategySubscription, StrategySignal, UserAlert, StrategyPerformance

@admin.register(Strategy)
class StrategyAdmin(admin.ModelAdmin):
    list_display = ['name', 'strategy_type', 'short_period', 'long_period', 'is_active', 'created_at']
    list_filter = ['strategy_type', 'is_active', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at']
    
    fieldsets = (
        (None, {
            'fields': ('name', 'description', 'strategy_type', 'is_active')
        }),
        ('Strategy Parameters', {
            'fields': ('short_period', 'long_period', 'min_volume', 'min_price')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

@admin.register(UserStrategySubscription)
class UserStrategySubscriptionAdmin(admin.ModelAdmin):
    list_display = ['user', 'strategy', 'ticker', 'is_active', 'subscribed_at', 'last_alert_sent']
    list_filter = ['is_active', 'subscribed_at', 'strategy__strategy_type']
    search_fields = ['user__username', 'strategy__name', 'ticker__ticker_symbol']
    readonly_fields = ['subscribed_at', 'last_alert_sent']
    
    fieldsets = (
        (None, {
            'fields': ('user', 'strategy', 'ticker', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('subscribed_at', 'last_alert_sent'),
            'classes': ('collapse',)
        }),
    )

@admin.register(StrategySignal)
class StrategySignalAdmin(admin.ModelAdmin):
    list_display = ['strategy', 'ticker', 'signal_type', 'trigger_price', 'short_ma_value', 'long_ma_value', 'triggered_at']
    list_filter = ['signal_type', 'triggered_at', 'strategy__strategy_type']
    search_fields = ['strategy__name', 'ticker__ticker_symbol']
    readonly_fields = ['triggered_at']
    date_hierarchy = 'triggered_at'
    
    fieldsets = (
        (None, {
            'fields': ('strategy', 'ticker', 'signal_type', 'trigger_price')
        }),
        ('Moving Average Values', {
            'fields': ('short_ma_value', 'long_ma_value', 'volume')
        }),
        ('Signal Metadata', {
            'fields': ('signal_strength', 'triggered_at')
        }),
    )

@admin.register(UserAlert)
class UserAlertAdmin(admin.ModelAdmin):
    list_display = ['user', 'get_strategy_name', 'get_ticker_symbol', 'get_signal_type', 'is_read', 'sent_at']
    list_filter = ['is_read', 'sent_at', 'email_sent', 'sms_sent']
    search_fields = ['user__username', 'subscription__strategy__name', 'signal__ticker__ticker_symbol', 'message']
    readonly_fields = ['sent_at', 'read_at']
    date_hierarchy = 'sent_at'
    
    actions = ['mark_as_read', 'mark_as_unread']
    
    fieldsets = (
        (None, {
            'fields': ('user', 'subscription', 'signal', 'message', 'is_read')
        }),
        ('Notifications', {
            'fields': ('email_sent', 'sms_sent')
        }),
        ('Timestamps', {
            'fields': ('sent_at', 'read_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_strategy_name(self, obj):
        return obj.signal.strategy.name
    get_strategy_name.short_description = 'Strategy'
    
    def get_ticker_symbol(self, obj):
        return obj.signal.ticker.ticker_symbol.upper()
    get_ticker_symbol.short_description = 'Ticker'
    
    def get_signal_type(self, obj):
        return obj.signal.signal_type
    get_signal_type.short_description = 'Signal Type'
    
    def mark_as_read(self, request, queryset):
        updated = 0
        for alert in queryset:
            if not alert.is_read:
                alert.mark_as_read()
                updated += 1
        self.message_user(request, f'{updated} alert(s) marked as read.')
    mark_as_read.short_description = "Mark selected alerts as read"
    
    def mark_as_unread(self, request, queryset):
        updated = queryset.update(is_read=False, read_at=None)
        self.message_user(request, f'{updated} alert(s) marked as unread.')
    mark_as_unread.short_description = "Mark selected alerts as unread"

@admin.register(StrategyPerformance)
class StrategyPerformanceAdmin(admin.ModelAdmin):
    list_display = ['strategy', 'ticker', 'total_signals', 'buy_signals', 'sell_signals', 'success_rate', 'last_updated']
    list_filter = ['strategy__strategy_type', 'last_updated']
    search_fields = ['strategy__name', 'ticker__ticker_symbol']
    readonly_fields = ['last_updated']
    date_hierarchy = 'last_updated'
