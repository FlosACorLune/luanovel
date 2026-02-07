# users/urls.py
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'users'

urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='users/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('bookmark/toggle/', views.toggle_bookmark, name='toggle_bookmark'),
    path('@<str:username>/', views.profile, name='profile'),
]