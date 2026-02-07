from django.db import models

class Genre(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)
    
    def __str__(self):
        return self.name


class Manga(models.Model):
    # Основная информация
    title = models.CharField(max_length=300, db_index=True)
    slug = models.SlugField(unique=True, db_index=True)
    alternative_titles = models.JSONField(default=list, blank=True)
    description = models.TextField(blank=True)
    
    # Ссылки
    cover_url = models.URLField()
    original_url = models.URLField()
    
    # Метаданные
    genres = models.ManyToManyField(Genre, blank=True, related_name='mangas')
    author = models.CharField(max_length=200, blank=True)
    artist = models.CharField(max_length=200, blank=True)
    year = models.IntegerField(null=True, blank=True)
    
    # Статистика
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
        ]
    
    def __str__(self):
        return self.title


class Chapter(models.Model):
    manga = models.ForeignKey(Manga, on_delete=models.CASCADE, related_name='chapters')
    number = models.FloatField()
    title = models.CharField(max_length=255, null=True, blank=True)
    volume = models.IntegerField(default=1)
    
    # Ссылка на контент
    url = models.URLField()
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