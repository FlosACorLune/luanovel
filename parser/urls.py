from django.urls import path
from . import views

app_name = 'parser'

urlpatterns = [
    path('search/', views.search, name='search'),
    path('api/search/', views.api_search, name='api_search'),
]