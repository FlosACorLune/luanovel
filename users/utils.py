from users.models import UserPreferences, MangaReadingSettings, ReadingProgress, ReadingHistory

def get_reading_orientation(user, manga):
    """
    Определяет ориентацию чтения для пользователя и манги
    Приоритет: индивидуальные настройки > глобальные настройки > тип контента
    """
    # 1. Проверяем индивидуальные настройки для этой манги
    try:
        settings = MangaReadingSettings.objects.get(user=user, manga=manga)
        if settings.reading_orientation != 'auto':
            return settings.reading_orientation
    except MangaReadingSettings.DoesNotExist:
        pass
    
    # 2. Проверяем глобальные настройки пользователя
    try:
        prefs = user.preferences
        if prefs.default_reading_orientation != 'auto':
            return prefs.default_reading_orientation
    except UserPreferences.DoesNotExist:
        pass
    
    # 3. Используем ориентацию по типу контента
    return manga.get_default_orientation()


def update_reading_progress(user, manga, chapter, page, total_pages):
    """
    Обновляет прогресс чтения
    """
    progress, created = ReadingProgress.objects.update_or_create(
        user=user,
        manga=manga,
        defaults={
            'chapter': chapter,
            'current_page': page,
            'total_pages': total_pages,
            'is_completed': page >= total_pages
        }
    )
    
    # Добавляем в историю (только если новая глава или прошло время)
    ReadingHistory.objects.create(
        user=user,
        manga=manga,
        chapter=chapter
    )
    
    return progress


def get_continue_reading(user, limit=10):
    """
    Получить список манги для продолжения чтения
    """
    return ReadingProgress.objects.filter(
        user=user,
        is_completed=False
    ).select_related('manga', 'chapter').order_by('-updated_at')[:limit]