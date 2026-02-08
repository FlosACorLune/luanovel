#manga/views.py
from django.shortcuts import render, get_object_or_404
from django.http import Http404
from manga.models import Manga, Chapter, Genre # Убрали ContentType
from parser.parsers import get_parser
from django.utils.text import slugify
from django.db import transaction
from users.models import ReadingProgress, Bookmark


def home(request):
    """
    Главная страница: показывает последние обновления из БД
    """
    # Убрали select_related('content_type'), так как модели больше нет
    mangas = Manga.objects.all().order_by('-updated_at')[:20]
    
    return render(request, 'manga/home.html', {
        'mangas': mangas,
    })


def manga_detail(request, slug):
    """
    Страница деталей манги
    """
    manga = Manga.objects.filter(slug=slug).first()
    
    current_status = None
    if request.user.is_authenticated:
        bookmark = Bookmark.objects.filter(user=request.user, manga=manga).first()
        if bookmark:
            current_status = bookmark.status
    
    if not manga:
        manga = _fetch_and_save_manga(slug)
    
    if not manga:
        raise Http404("Манга не найдена")
    
    chapters = manga.chapters.all().order_by('number')
    
    if not chapters.exists():
        _fetch_and_save_chapters(manga, slug)
        chapters = manga.chapters.all().order_by('number')
    
    return render(request, 'manga/detail.html', {
        'manga': manga,
        'chapters': chapters,
        'current_status': current_status,
    })



def chapter_reader(request, slug, volume, number):
    # Превращаем строку '10.5' в число 10.5 для поиска в базе
    try:
        num_float = float(number)
    except ValueError:
        raise Http404("Неверный формат номера главы")

    # Ищем главу, используя связь через manga__slug
    chapter = get_object_or_404(
        Chapter.objects.select_related('manga'), 
        manga__slug=slug, 
        volume=volume, 
        number=num_float
    )
    
    manga = chapter.manga
    
    # Парсинг страниц
    parser = get_parser('mangalib')
    pages = parser.get_pages(manga.slug, chapter.volume, chapter.number)
    
    # Сохранение прогресса
    if request.user.is_authenticated:
        ReadingProgress.objects.update_or_create(
            user=request.user,
            manga=manga,
            defaults={'last_chapter': chapter}
        )
    
    # Соседние главы
    prev_chapter = Chapter.objects.filter(manga=manga, number__lt=chapter.number).order_by('-number').first()
    next_chapter = Chapter.objects.filter(manga=manga, number__gt=chapter.number).order_by('number').first()
    
    return render(request, 'manga/reader.html', {
        'chapter': chapter,
        'manga': chapter.manga,
        'pages': pages,
        'prev_chapter': prev_chapter,
        'next_chapter': next_chapter,
    })


def _fetch_and_save_manga(slug):
    """
    Парсит мангу и сохраняет в БД
    """
    parser = get_parser('mangalib')
    
    if not parser:
        return None
    
    try:
        details = parser.get_manga_details(slug)
        if not details:
            return None
        
        # Полностью удалена логика ContentType
        
        with transaction.atomic():
            manga = Manga.objects.create(
                title=details['title'],
                slug=slug,
                description=details.get('description', ''),
                cover_url=details.get('cover_url', ''),
                original_url=details.get('original_url', ''),
                author=details.get('author', ''),
                artist=details.get('artist', ''),
                year=details.get('year'),
                total_chapters=details.get('total_chapters', 0),
                # Убрали status='ongoing'
            )
            
            if details.get('genres'):
                for genre_name in details['genres']:
                    genre, _ = Genre.objects.get_or_create(
                        name=genre_name,
                        defaults={'slug': slugify(genre_name, allow_unicode=True) or f"genre-{genre_name[:10]}"}
                    )
                    manga.genres.add(genre)
        
        return manga
        
    except Exception as e:
        print(f"Error fetching manga {slug}: {e}")
        return None


def _fetch_and_save_chapters(manga, slug):
    parser = get_parser('mangalib')
    if not parser:
        return
    
    try:
        chapters_data = parser.get_chapters(slug)
        if not chapters_data:
            return
        
        with transaction.atomic():
            for chapter_data in chapters_data:
                Chapter.objects.get_or_create(
                    manga=manga,
                    number=chapter_data['number'],
                    defaults={
                        'title': chapter_data.get('title') or '', 
                        'url': chapter_data.get('url') or '',
                        'volume': chapter_data.get('volume', 1),
                    }
                )
            
            manga.total_chapters = manga.chapters.count()
            manga.save(update_fields=['total_chapters'])
        
    except Exception as e:
        print(f"Error fetching chapters for {slug}: {e}")