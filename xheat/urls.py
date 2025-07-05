from django.urls import path
from . import views

urlpatterns = [
    path('', views.heatmap_view, name='heatmap'),
    path('api/heatmap-data/', views.heatmap_data, name='heatmap_data'),
    path('api/sector-summary/', views.sector_summary, name='sector_summary'),
] 