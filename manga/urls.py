from django.urls import path
from . import views

app_name = 'manga'

urlpatterns = [
    path('', views.home, name='home'),
    path('manga/<slug:slug>/', views.manga_detail, name='detail'),
]