from django.core.management.base import BaseCommand
from xalert.models import Strategy

class Command(BaseCommand):
    help = 'Create default trading strategies for the xalert app'

    def handle(self, *args, **options):
        strategies = [
            {
                'name': 'Golden Cross 20/50',
                'description': 'Classic bullish signal when 20-day MA crosses above 50-day MA, and bearish when it crosses below. Ideal for medium-term trend following.',
                'strategy_type': 'MA_CROSSOVER',
                'short_period': 20,
                'long_period': 50,
                'min_volume': 100000,
                'min_price': 10.00
            },
            {
                'name': 'Fast Cross 10/20',
                'description': 'Quick moving average crossover strategy for short-term trading. More sensitive to price changes but may generate more false signals.',
                'strategy_type': 'MA_CROSSOVER',
                'short_period': 10,
                'long_period': 20,
                'min_volume': 50000,
                'min_price': 5.00
            },
            {
                'name': 'Slow Cross 50/100',
                'description': 'Conservative long-term strategy using 50 and 100-day moving averages. Fewer signals but higher reliability for trend changes.',
                'strategy_type': 'MA_CROSSOVER',
                'short_period': 50,
                'long_period': 100,
                'min_volume': 200000,
                'min_price': 20.00
            },
            {
                'name': 'Breakout Above 20/50',
                'description': 'Alerts when price breaks above both 20 and 50-day moving averages with strong momentum. Good for catching breakouts.',
                'strategy_type': 'MA_BREAKOUT',
                'short_period': 20,
                'long_period': 50,
                'min_volume': 150000,
                'min_price': 15.00
            },
            {
                'name': 'Support Bounce 20/50',
                'description': 'Identifies when price bounces off moving average support levels. Useful for buying at support and selling at resistance.',
                'strategy_type': 'MA_SUPPORT',
                'short_period': 20,
                'long_period': 50,
                'min_volume': 75000,
                'min_price': 8.00
            },
            {
                'name': 'Weekly Cross 5/10',
                'description': 'Short-term strategy using 5 and 10-day moving averages. Very responsive but requires careful risk management due to frequent signals.',
                'strategy_type': 'MA_CROSSOVER',
                'short_period': 5,
                'long_period': 10,
                'min_volume': 25000,
                'min_price': 3.00
            }
        ]

        created_count = 0
        updated_count = 0

        for strategy_data in strategies:
            strategy, created = Strategy.objects.get_or_create(
                name=strategy_data['name'],
                defaults=strategy_data
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created strategy: {strategy.name}')
                )
            else:
                # Update existing strategy with new data
                for key, value in strategy_data.items():
                    if key != 'name':  # Don't update the name
                        setattr(strategy, key, value)
                strategy.save()
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f'Updated existing strategy: {strategy.name}')
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'\nSummary: {created_count} strategies created, {updated_count} strategies updated'
            )
        )
        
        # Display all active strategies
        self.stdout.write('\nActive Strategies:')
        for strategy in Strategy.objects.filter(is_active=True):
            self.stdout.write(f'- {strategy.name} (MA{strategy.short_period}/{strategy.long_period})')
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\nTotal active strategies: {Strategy.objects.filter(is_active=True).count()}'
            )
        ) 