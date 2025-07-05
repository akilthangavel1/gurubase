from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db import connection, models
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
import pandas as pd
from .models import Strategy, UserStrategySubscription, StrategySignal, UserAlert, StrategyPerformance
from dashboard.models import TickerBase

@login_required
def strategy_dashboard(request):
    """Display the main strategy dashboard with available strategies and user subscriptions"""
    # Get all available strategies
    available_strategies = Strategy.objects.filter(is_active=True)
    
    # Get user's current subscriptions
    user_subscriptions = UserStrategySubscription.objects.filter(
        user=request.user, is_active=True
    ).select_related('strategy', 'ticker')
    
    # Get recent signals for subscribed strategies
    subscribed_strategy_ids = user_subscriptions.values_list('strategy_id', flat=True)
    recent_signals = StrategySignal.objects.filter(
        strategy_id__in=subscribed_strategy_ids,
        signal_type__in=['BUY', 'SELL']
    ).select_related('strategy', 'ticker').order_by('-triggered_at')[:10]
    
    # Get user's recent alerts
    user_alerts = UserAlert.objects.filter(
        user=request.user
    ).select_related('signal__strategy', 'signal__ticker').order_by('-sent_at')[:10]
    
    # Get unread alerts count
    unread_alerts_count = UserAlert.objects.filter(user=request.user, is_read=False).count()
    
    context = {
        'available_strategies': available_strategies,
        'user_subscriptions': user_subscriptions,
        'recent_signals': recent_signals,
        'user_alerts': user_alerts,
        'unread_alerts_count': unread_alerts_count,
        'total_subscriptions': user_subscriptions.count(),
    }
    return render(request, 'xalert/dashboard.html', context)

@login_required
def subscribe_strategy(request):
    """Subscribe to a strategy"""
    if request.method == 'POST':
        strategy_id = request.POST.get('strategy')
        ticker_id = request.POST.get('ticker')  # Optional: can be null for all tickers
        
        try:
            strategy = Strategy.objects.get(id=strategy_id, is_active=True)
            ticker = None
            
            if ticker_id:
                ticker = TickerBase.objects.get(id=ticker_id)
            
            # Create or get subscription
            subscription, created = UserStrategySubscription.objects.get_or_create(
                user=request.user,
                strategy=strategy,
                ticker=ticker,
                defaults={'is_active': True}
            )
            
            if created:
                ticker_info = f" for {ticker.ticker_symbol}" if ticker else " (All Tickers)"
                messages.success(request, f'Successfully subscribed to {strategy.name}{ticker_info}')
            else:
                if not subscription.is_active:
                    subscription.is_active = True
                    subscription.save()
                    messages.success(request, f'Reactivated subscription to {strategy.name}')
                else:
                    messages.info(request, f'You are already subscribed to {strategy.name}')
            
            return redirect('xalert:strategy_dashboard')
            
        except Strategy.DoesNotExist:
            messages.error(request, 'Invalid strategy selected')
        except TickerBase.DoesNotExist:
            messages.error(request, 'Invalid ticker selected')
        except Exception as e:
            messages.error(request, f'Error subscribing to strategy: {str(e)}')
    
    # GET request - show subscription form
    strategies = Strategy.objects.filter(is_active=True)
    tickers = TickerBase.objects.all().order_by('ticker_symbol')
    return render(request, 'xalert/subscribe_strategy.html', {
        'strategies': strategies,
        'tickers': tickers
    })

@login_required
def unsubscribe_strategy(request, subscription_id):
    """Unsubscribe from a strategy"""
    subscription = get_object_or_404(UserStrategySubscription, id=subscription_id, user=request.user)
    strategy_name = subscription.strategy.name
    ticker_info = f" for {subscription.ticker.ticker_symbol}" if subscription.ticker else ""
    
    subscription.is_active = False
    subscription.save()
    
    messages.success(request, f'Unsubscribed from {strategy_name}{ticker_info}')
    return redirect('xalert:strategy_dashboard')

@login_required
def strategy_details(request, strategy_id):
    """Show detailed information about a strategy"""
    strategy = get_object_or_404(Strategy, id=strategy_id, is_active=True)
    
    # Get recent signals for this strategy
    recent_signals = StrategySignal.objects.filter(
        strategy=strategy
    ).select_related('ticker').order_by('-triggered_at')[:20]
    
    # Get strategy performance
    performance = StrategyPerformance.objects.filter(strategy=strategy).first()
    
    # Check if user is subscribed
    user_subscription = None
    if request.user.is_authenticated:
        user_subscription = UserStrategySubscription.objects.filter(
            user=request.user, strategy=strategy, is_active=True
        ).first()
    
    context = {
        'strategy': strategy,
        'recent_signals': recent_signals,
        'performance': performance,
        'user_subscription': user_subscription,
    }
    return render(request, 'xalert/strategy_details.html', context)

@login_required
def user_alerts(request):
    """Display user's alerts with filtering and marking as read"""
    alerts = UserAlert.objects.filter(
        user=request.user
    ).select_related('signal__strategy', 'signal__ticker').order_by('-sent_at')
    
    # Filter by read status if requested
    read_filter = request.GET.get('read')
    if read_filter == 'unread':
        alerts = alerts.filter(is_read=False)
    elif read_filter == 'read':
        alerts = alerts.filter(is_read=True)
    
    # Mark alerts as read if requested
    if request.method == 'POST':
        alert_ids = request.POST.getlist('mark_read')
        if alert_ids:
            marked_count = 0
            for alert_id in alert_ids:
                try:
                    alert = UserAlert.objects.get(id=alert_id, user=request.user)
                    if not alert.is_read:
                        alert.mark_as_read()
                        marked_count += 1
                except UserAlert.DoesNotExist:
                    pass
            
            if marked_count > 0:
                messages.success(request, f'{marked_count} alert(s) marked as read')
        
        return redirect('xalert:user_alerts')
    
    return render(request, 'xalert/user_alerts.html', {'alerts': alerts})

def execute_strategy(strategy, ticker_symbol, days=100):
    """Execute a strategy on a ticker and return signals"""
    try:
        # Get historical data from the dynamically created table
        table_name = f"{ticker_symbol.lower()}_historical_data"
        
        with connection.cursor() as cursor:
            query = f"""
                SELECT datetime, close_price, volume 
                FROM "{table_name}" 
                ORDER BY datetime DESC 
                LIMIT %s
            """
            cursor.execute(query, [days])
            data = cursor.fetchall()
        
        if len(data) < max(strategy.short_period, strategy.long_period):
            return None
        
        # Convert to DataFrame for easier calculation
        df = pd.DataFrame(data, columns=['datetime', 'close_price', 'volume'])
        df['datetime'] = pd.to_datetime(df['datetime'])
        df = df.sort_values('datetime')
        df['close_price'] = df['close_price'].astype(float)
        df['volume'] = df['volume'].astype(int)
        
        # Calculate moving averages
        df['short_ma'] = df['close_price'].rolling(window=strategy.short_period).mean()
        df['long_ma'] = df['close_price'].rolling(window=strategy.long_period).mean()
        
        # Detect signals based on strategy type
        df['short_ma_prev'] = df['short_ma'].shift(1)
        df['long_ma_prev'] = df['long_ma'].shift(1)
        
        def get_signal(row):
            if pd.isna(row['short_ma']) or pd.isna(row['long_ma']) or pd.isna(row['short_ma_prev']) or pd.isna(row['long_ma_prev']):
                return 'NEUTRAL'
            
            if strategy.strategy_type == 'MA_CROSSOVER':
                # Bullish crossover: Short MA crosses above Long MA
                if row['short_ma_prev'] <= row['long_ma_prev'] and row['short_ma'] > row['long_ma']:
                    return 'BUY'
                # Bearish crossover: Short MA crosses below Long MA
                elif row['short_ma_prev'] >= row['long_ma_prev'] and row['short_ma'] < row['long_ma']:
                    return 'SELL'
            
            elif strategy.strategy_type == 'MA_BREAKOUT':
                # Price breaks above both MAs
                if row['close_price'] > row['short_ma'] and row['close_price'] > row['long_ma'] and row['short_ma'] > row['long_ma']:
                    return 'BUY'
                # Price breaks below both MAs
                elif row['close_price'] < row['short_ma'] and row['close_price'] < row['long_ma'] and row['short_ma'] < row['long_ma']:
                    return 'SELL'
            
            elif strategy.strategy_type == 'MA_SUPPORT':
                # Price bounces off MA support
                if row['close_price'] >= row['short_ma'] and row['short_ma'] > row['long_ma']:
                    return 'BUY'
                elif row['close_price'] <= row['short_ma'] and row['short_ma'] < row['long_ma']:
                    return 'SELL'
            
            return 'NEUTRAL'
        
        df['signal'] = df.apply(get_signal, axis=1)
        
        return df
        
    except Exception as e:
        print(f"Error executing strategy {strategy.name} for {ticker_symbol}: {str(e)}")
        return None

@login_required
def run_strategies(request):
    """Run all active strategies and generate signals (for manual testing)"""
    if request.method == 'POST':
        active_strategies = Strategy.objects.filter(is_active=True)
        tickers = TickerBase.objects.all()
        
        signals_generated = 0
        alerts_sent = 0
        
        for strategy in active_strategies:
            for ticker in tickers:
                # Execute strategy
                df = execute_strategy(strategy, ticker.ticker_symbol)
                
                if df is not None and len(df) > 0:
                    latest = df.iloc[-1]
                    
                    # Check if this is a new signal
                    if latest['signal'] in ['BUY', 'SELL']:
                        # Create or update signal
                        signal, created = StrategySignal.objects.get_or_create(
                            strategy=strategy,
                            ticker=ticker,
                            triggered_at__date=latest['datetime'].date(),
                            defaults={
                                'signal_type': latest['signal'],
                                'trigger_price': Decimal(str(latest['close_price'])),
                                'short_ma_value': Decimal(str(latest['short_ma'])) if not pd.isna(latest['short_ma']) else Decimal('0'),
                                'long_ma_value': Decimal(str(latest['long_ma'])) if not pd.isna(latest['long_ma']) else Decimal('0'),
                                'volume': int(latest['volume']) if not pd.isna(latest['volume']) else 0,
                            }
                        )
                        
                        if created:
                            signals_generated += 1
                            
                            # Send alerts to subscribed users
                            subscriptions = UserStrategySubscription.objects.filter(
                                strategy=strategy,
                                is_active=True
                            ).filter(
                                models.Q(ticker=ticker) | models.Q(ticker__isnull=True)
                            )
                            
                            for subscription in subscriptions:
                                message = f"{strategy.name}: {signal.signal_type} signal for {ticker.ticker_symbol} at ₹{signal.trigger_price}"
                                
                                UserAlert.objects.create(
                                    user=subscription.user,
                                    subscription=subscription,
                                    signal=signal,
                                    message=message
                                )
                                alerts_sent += 1
                                
                                # Update subscription's last alert time
                                subscription.last_alert_sent = timezone.now()
                                subscription.save()
        
        return JsonResponse({
            'success': True,
            'signals_generated': signals_generated,
            'alerts_sent': alerts_sent,
            'message': f'Generated {signals_generated} signals and sent {alerts_sent} alerts.'
        })
    
    return JsonResponse({'success': False, 'message': 'Invalid request method'})

@login_required
def strategy_performance(request, strategy_id):
    """Show strategy performance analytics"""
    strategy = get_object_or_404(Strategy, id=strategy_id)
    
    # Get signals for analysis
    signals = StrategySignal.objects.filter(strategy=strategy).order_by('-triggered_at')
    
    # Calculate basic performance metrics
    total_signals = signals.count()
    buy_signals = signals.filter(signal_type='BUY').count()
    sell_signals = signals.filter(signal_type='SELL').count()
    
    # Get recent performance
    thirty_days_ago = timezone.now() - timedelta(days=30)
    recent_signals = signals.filter(triggered_at__gte=thirty_days_ago)
    
    context = {
        'strategy': strategy,
        'total_signals': total_signals,
        'buy_signals': buy_signals,
        'sell_signals': sell_signals,
        'recent_signals': recent_signals[:20],
        'signals_30_days': recent_signals.count(),
    }
    
    return render(request, 'xalert/strategy_performance.html', context)
