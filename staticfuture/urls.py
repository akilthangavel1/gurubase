from django.urls import path
from . import views

urlpatterns = [
    path('', views.static_future_data, name='static_future_data'),
    path('sse-dynamic-data/', views.sse_static_future_data, name='sse_static_future_data'),
]