from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('features/', views.features, name='features'),
    path('live-stocks/', views.live_stocks, name='live-stocks'),
    path('login/', views.login, name='login'),
    path('portfolio/', views.portfolio, name='portfolio'),
    path('register/', views.register, name='register'),
    path('trending-stocks/', views.trending_stocks, name='trending-stocks'),
    path('stocks/', views.stocks, name='stocks'),
    path('futures/', views.futures, name='futures'),
    path('futures/scanner/', views.future_scanner, name='future-scanner'),
    path('options/', views.options, name='options'),
    path('api/stocks/stream/', views.sse_stocks_data, name='sse_stocks_data'),
    path('historical-data/', views.view_historical_data, name='historical_data'),
    path('historical-data/<str:ticker_symbol>/', views.view_historical_data, name='historical_data_ticker'),
] 