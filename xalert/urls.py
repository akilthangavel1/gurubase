from django.urls import path
from . import views

app_name = 'xalert'

urlpatterns = [
    path('', views.strategy_dashboard, name='strategy_dashboard'),
    path('subscribe/', views.subscribe_strategy, name='subscribe_strategy'),
    path('unsubscribe/<int:subscription_id>/', views.unsubscribe_strategy, name='unsubscribe_strategy'),
    path('strategy/<int:strategy_id>/', views.strategy_details, name='strategy_details'),
    path('strategy/<int:strategy_id>/performance/', views.strategy_performance, name='strategy_performance'),
    path('alerts/', views.user_alerts, name='user_alerts'),
    path('run-strategies/', views.run_strategies, name='run_strategies'),
] 