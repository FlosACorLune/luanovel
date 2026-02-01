from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from users.models import UserPreferences

@receiver(post_save, sender=User)
def create_user_preferences(sender, instance, created, **kwargs):
    """Автоматически создаем настройки для нового пользователя"""
    if created:
        UserPreferences.objects.create(user=instance)