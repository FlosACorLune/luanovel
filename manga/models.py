from django.db import models
from django.contrib.auth.models import User

class ContentType(models.Model):
    """
    Типы контента: Manga, Manhwa, Manhua и т.д.
    Легко добавлять новые типы
    """
    name = models.CharField(max_length=50, unique=True)  # Manga, Manhwa, Manhua
    default_orientation = models.CharField(
        max_length=20,
        choices=[
            ('horizontal', 'Horizontal'),
            ('vertical', 'Vertical'),
        ],
        default='horizontal'
    )
    description = models.TextField(blank=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "Content Type"
        verbose_name_plural = "Content Types"


class Genre(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)
    
    def __str__(self):
        return self.name


class Manga(models.Model):
    STATUS_CHOICES = [
        ('ongoing', 'Ongoing'),
        ('completed', 'Completed'),
        ('hiatus', 'Hiatus'),
        ('cancelled', 'Cancelled'),
    ]
    
    # Основная информация
    title = models.CharField(max_length=300, db_index=True)
    slug = models.SlugField(unique=True, db_index=True)
    alternative_titles = models.JSONField(default=list, blank=True)  # ["Title 1", "Title 2"]
    description = models.TextField(blank=True)
    
    # Тип контента (Manga/Manhwa/Manhua)
    content_type = models.ForeignKey(
        ContentType, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='mangas'
    )
    
    # Ссылки
    cover_url = models.URLField()
    original_url = models.URLField()
    
    # Метаданные
    genres = models.ManyToManyField(Genre, blank=True, related_name='mangas')
    author = models.CharField(max_length=200, blank=True)
    artist = models.CharField(max_length=200, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ongoing')
    year = models.IntegerField(null=True, blank=True)
    
    # Статистика (можно обновлять периодически)
    total_chapters = models.IntegerField(default=0)
    views_count = models.IntegerField(default=0)
    bookmarks_count = models.IntegerField(default=0)
    
    # Даты
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['-updated_at']),
            models.Index(fields=['content_type']),
        ]
    
    def __str__(self):
        return self.title
    
    def get_default_orientation(self):
        """Получить ориентацию по умолчанию для этой манги"""
        if self.content_type:
            return self.content_type.default_orientation
        return 'horizontal'


class Chapter(models.Model):
    manga = models.ForeignKey(Manga, on_delete=models.CASCADE, related_name='chapters')
    number = models.FloatField()  # 1, 1.5, 2 и т.д.
    title = models.CharField(max_length=300, blank=True)
    
    # Ссылка на оригинал
    url = models.URLField()
    
    # Количество страниц (можно парсить заранее или налету)
    pages_count = models.IntegerField(default=0)
    
    # Даты
    release_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-number']
        unique_together = ['manga', 'number']
        indexes = [
            models.Index(fields=['manga', '-number']),
        ]
    
    def __str__(self):
        return f"{self.manga.title} - Ch. {self.number}"