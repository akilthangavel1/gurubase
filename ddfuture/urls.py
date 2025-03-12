from django.urls import path
from . import views

urlpatterns = [
    path('', views.future_dynamic_data, name='future_dynamic_data'),
    path('sse-dynamic-data/', views.sse_dynamic_data, name='sse_dynamic_data'),
]