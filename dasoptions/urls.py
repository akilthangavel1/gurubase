from django.urls import path
from . import views


urlpatterns = [
    path("", views.table_stream, name="table_stream"),
    path('option-chain/', views.option_chain_view, name='option_chain_view'),
]