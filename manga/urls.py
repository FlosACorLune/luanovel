from django.urls import path
from . import views

app_name = 'manga'

urlpatterns = [
    path('', views.home, name='home'),
    
    path('search/', views.search, name='search'),
    path('api/search/', views.api_search, name='api_search'),
    
    path('manga/<str:source>/<slug:slug>/', views.manga_detail, name='detail_with_source'),
    path('manga/<slug:slug>/', views.manga_detail, name='detail'),
    
    path('manga/<str:source>/<slug:slug>/v<int:volume>/c<str:number>/', 
         views.chapter_reader, name='reader_with_source'),
    path('manga/<slug:slug>/v<int:volume>/c<str:number>/', 
         views.chapter_reader, name='reader'),
    
    path('manga/<str:source>/<slug:slug>/v<int:volume>/c<str:number>/download/', 
         views.download_chapter_zip, name='download_chapter_with_source'),
    path('manga/<slug:slug>/v<int:volume>/c<str:number>/download/', 
         views.download_chapter_zip, name='download_chapter'),
]