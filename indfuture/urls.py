from django.urls import path
from . import views

urlpatterns = [
    path('', views.indicator_future, name='indicator_future'),
    path('stream_indicator_data/', views.stream_indicator_data, name='stream_indicator_data'),
]
