from django.urls import path
from . import views

app_name = 'manga'

urlpatterns = [
    # Главная страница
    path('', views.home, name='home'),
    
    # Детали манги
    path('manga/<slug:slug>/', views.manga_detail, name='detail'),
    
    # Читалка главы
    path('reader/<int:chapter_id>/', views.chapter_reader, name='reader'),
]