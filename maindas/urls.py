from django.urls import path
from . import views
from .dynamicdata import send_sse_dynamic_data


urlpatterns = [
    path('', views.display_main_dashboard, name='maindashboard'),
    path('stream-dynamic-data/', send_sse_dynamic_data, name='stream_dynamic_data'),
]
