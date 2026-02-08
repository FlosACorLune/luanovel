from django.urls import path
from . import views

app_name = 'manga'

urlpatterns = [
    # Главная страница
    path('', views.home, name='home'),
    
    # Детали манги
    path('manga/<slug:slug>/', views.manga_detail, name='detail'),
    
    # Читалка главы
    path('manga/<slug:slug>/v<int:volume>/c<str:number>/', views.chapter_reader, name='reader'),
    path('manga/<slug:slug>/v<int:volume>/c<str:number>/download/', 
         views.download_chapter_zip, name='download_chapter'),
]