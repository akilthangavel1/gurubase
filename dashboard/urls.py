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
    path('tickers/', views.ticker_list, name='ticker_list'),
    path('tickers/create/', views.ticker_create, name='ticker_create'),
    path('tickers/<int:pk>/update/', views.ticker_update, name='ticker_update'),
    path('tickers/<int:pk>/delete/', views.ticker_delete, name='ticker_delete'),
] 