from django.db import models
from django.contrib.auth.models import User
from manga.models import Manga, Chapter

class UserPreferences(models.Model):
    """
    Глобальные настройки пользователя
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='preferences')
    
    # Настройки чтения по умолчанию
    default_reading_orientation = models.CharField(
        max_length=20,
        choices=[
            ('auto', 'Auto (by content type)'),  # по типу контента
            ('horizontal', 'Horizontal'),
            ('vertical', 'Vertical'),
        ],
        default='auto'
    )
    
    # Другие глобальные настройки
    default_reading_mode = models.CharField(
        max_length=20,
        choices=[
            ('single', 'Single Page'),
            ('double', 'Double Page'),
            ('long_strip', 'Long Strip'),
        ],
        default='single'
    )
    
    auto_mark_as_read = models.BooleanField(default=True)
    show_comments = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username}'s preferences"
    
    class Meta:
        verbose_name = "User Preference"
        verbose_name_plural = "User Preferences"


class MangaReadingSettings(models.Model):
    """
    Индивидуальные настройки чтения для конкретной манги
    Переопределяют глобальные настройки
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    manga = models.ForeignKey(Manga, on_delete=models.CASCADE)
    
    # Настройки для этой конкретной манги
    reading_orientation = models.CharField(
        max_length=20,
        choices=[
            ('auto', 'Auto'),
            ('horizontal', 'Horizontal'),
            ('vertical', 'Vertical'),
        ],
        default='auto'
    )
    
    reading_mode = models.CharField(
        max_length=20,
        choices=[
            ('single', 'Single Page'),
            ('double', 'Double Page'),
            ('long_strip', 'Long Strip'),
        ],
        null=True,
        blank=True
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'manga']
        verbose_name = "Manga Reading Setting"
        verbose_name_plural = "Manga Reading Settings"
    
    def __str__(self):
        return f"{self.user.username} - {self.manga.title} settings"


class Bookmark(models.Model):
    """
    Закладки (избранное)
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookmarks')
    manga = models.ForeignKey(Manga, on_delete=models.CASCADE, related_name='bookmarked_by')
    
    # Можно добавить папки/категории
    folder = models.CharField(max_length=100, blank=True, default='default')
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'manga']
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} bookmarked {self.manga.title}"


class ReadingProgress(models.Model):
    """
    Текущий прогресс чтения (на какой главе и странице остановился)
    Только ПОСЛЕДНЯЯ прочитанная глава
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reading_progress')
    manga = models.ForeignKey(Manga, on_delete=models.CASCADE, related_name='user_progress')
    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE)
    
    # Текущая страница в главе
    current_page = models.IntegerField(default=1)
    total_pages = models.IntegerField(default=0)
    
    # Прочитано ли полностью
    is_completed = models.BooleanField(default=False)
    
    # Даты
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'manga']
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['user', '-updated_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.manga.title} Ch.{self.chapter.number} Page {self.current_page}"
    
    @property
    def progress_percentage(self):
        """Процент прочтения главы"""
        if self.total_pages > 0:
            return (self.current_page / self.total_pages) * 100
        return 0


class ReadingHistory(models.Model):
    """
    Полная история чтения (все главы которые читал)
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reading_history')
    manga = models.ForeignKey(Manga, on_delete=models.CASCADE)
    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE)
    
    # Когда читал
    read_at = models.DateTimeField(auto_now_add=True)
    
    # Сколько времени потратил на чтение (опционально)
    reading_duration = models.IntegerField(null=True, blank=True, help_text="Seconds")
    
    class Meta:
        ordering = ['-read_at']
        indexes = [
            models.Index(fields=['user', '-read_at']),
            models.Index(fields=['user', 'manga', '-read_at']),
        ]
        verbose_name = "Reading History"
        verbose_name_plural = "Reading Histories"
    
    def __str__(self):
        return f"{self.user.username} read {self.manga.title} Ch.{self.chapter.number}"