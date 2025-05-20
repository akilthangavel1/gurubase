from django.urls import path
from . import views
from .dynamicdata import send_sse_dynamic_data
from .staticdata import sse_static_future_data
from .indfuture import stream_indicator_data


urlpatterns = [
    path('', views.display_main_dashboard, name='maindashboard'),
    path('stream-dynamic-data/', send_sse_dynamic_data, name='stream_dynamic_data'),
    path('sse-static-data/', sse_static_future_data, name='sse_static_future_data'),
    path('stream_indicator_data/', stream_indicator_data, name='stream_indicator_data'),
]
