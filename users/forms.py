# users/forms.py
from django import forms  # Исправлено здесь
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

class UserRegisterForm(UserCreationForm):
    # Добавляем поле email как обязательное (по желанию)
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ['username', 'email']