from django.db import models
from django.contrib.auth.models import User
from manga.models import Manga, Chapter

class Profile(models.Model):
    """
    Расширение юзера: настройки и статус
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    
    is_vertical = models.BooleanField(default=True, verbose_name="Vertical Reading")
    
    def __str__(self):
        return f"Profile: {self.user.username}"

class Bookmark(models.Model):
    """
    Список избранного / Букмарки
    """
    STATUS_CHOICES = [
        ('reading', 'Reading'),
        ('planned', 'Planned'),
        ('completed', 'Completed'),
        ('dropped', 'Dropped'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookmarks')
    manga = models.ForeignKey(Manga, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='planned')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'manga']

class ReadingProgress(models.Model):
    """
    История: что читал и где остановился
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='history')
    manga = models.ForeignKey(Manga, on_delete=models.CASCADE)
    last_chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['user', 'manga']
        ordering = ['-updated_at']