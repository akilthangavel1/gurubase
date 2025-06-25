from django.urls import path
from django.shortcuts import render
from . import views
from .dynamicdata import send_sse_dynamic_data
from .staticdata import sse_static_future_data
from .indfuture import stream_indicator_data


urlpatterns = [
    path('', views.dashboard, name='maindashboard'),
    # Legacy individual SSE endpoints (can be kept for backward compatibility)
    path('stream-dynamic-data/', send_sse_dynamic_data, name='stream_dynamic_data'),
    path('sse-static-data/', sse_static_future_data, name='sse_static_future_data'),
    path('stream_indicator_data/', stream_indicator_data, name='stream_indicator_data'),
    
    # New unified SSE endpoint
    path('unified-stream/', views.unified_sse_stream, name='unified_sse_stream'),
    
    # Example page to demonstrate unified SSE
    path('unified-example/', lambda request: render(request, 'maindas/unified_sse_example.html'), name='unified_sse_example'),
]
