from django.shortcuts import render, get_object_or_404
from django.http import Http404
from manga.models import Manga, Chapter, ContentType, Genre
from parser.parsers import get_parser
from django.utils.text import slugify
from django.db import transaction


def home(request):
    """
    Главная страница
    Показывает недавно добавленные манги из БД
    """
    source = request.GET.get('source', 'all')
    
    # Показываем манги из БД (если есть)
    mangas = Manga.objects.all().select_related('content_type').order_by('-updated_at')[:20]
    
    return render(request, 'manga/home.html', {
        'mangas': mangas,
    })


def manga_detail(request, slug):
    """
    Страница деталей манги
    
    Поток работы:
    1. Ищем мангу в БД по slug
    2. Если не найдена - парсим с MangaLib и сохраняем
    3. Если главы не загружены - парсим главы
    4. Показываем страницу с деталями и списком глав
    """
    # Пытаемся найти в базе данных
    manga = Manga.objects.filter(slug=slug).select_related('content_type').first()
    
    # Если не нашли, пробуем спарсить
    if not manga:
        manga = _fetch_and_save_manga(slug)
    
    # Если всё равно не нашли - 404
    if not manga:
        raise Http404("Манга не найдена")
    
    # Получаем главы
    chapters = manga.chapters.all().order_by('number')  # От меньшего к большему
    
    # Если глав нет, пробуем спарсить
    if not chapters.exists():
        _fetch_and_save_chapters(manga, slug)
        chapters = manga.chapters.all().order_by('number')
    
    return render(request, 'manga/detail.html', {
        'manga': manga,
        'chapters': chapters
    })


def chapter_reader(request, chapter_id):
    chapter = get_object_or_404(Chapter.objects.select_related('manga'), id=chapter_id)
    
    # Получаем страницы через парсер
    parser = get_parser('mangalib')
    pages = parser.get_pages(chapter.manga.slug, chapter.volume, chapter.number)
    
    # Логика для кнопок навигации (у вас уже была)
    prev_chapter = Chapter.objects.filter(manga=chapter.manga, number__lt=chapter.number).order_by('-number').first()
    next_chapter = Chapter.objects.filter(manga=chapter.manga, number__gt=chapter.number).order_by('number').first()
    
    return render(request, 'manga/reader.html', {
        'chapter': chapter,
        'pages': pages,  # Теперь этот список уйдет в шаблон
        'prev_chapter': prev_chapter,
        'next_chapter': next_chapter,
    })
def _fetch_and_save_manga(slug):
    """
    Парсит мангу с MangaLib и сохраняет в БД
    
    Args:
        slug: Slug манги (например: "7965--chainsaw-man")
    
    Returns:
        Manga object или None если не найдена
    """
    parser = get_parser('mangalib')
    
    if not parser:
        print("Parser MangaLib not found")
        return None
    
    try:
        # Получаем детали с парсера
        details = parser.get_manga_details(slug)
        
        if not details:
            print(f"Manga {slug} not found in MangaLib")
            return None
        
        # Получаем или создаём тип контента
        content_type_name = details.get('content_type', 'Manga')
        content_type, _ = ContentType.objects.get_or_create(
            name=content_type_name,
            defaults={
                'default_orientation': 'vertical' if content_type_name in ['Manhwa', 'Manhua'] else 'horizontal'
            }
        )
        
        # Создаём мангу в транзакции
        with transaction.atomic():
            manga = Manga.objects.create(
                title=details['title'],
                slug=slug,
                description=details.get('description', ''),
                content_type=content_type,
                cover_url=details.get('cover_url', ''),
                original_url=details.get('original_url', ''),
                author=details.get('author', ''),
                artist=details.get('artist', ''),
                year=details.get('year'),
                total_chapters=details.get('total_chapters', 0),
                status='ongoing'
            )
            
            # Добавляем жанры
            if details.get('genres'):
                for genre_name in details['genres']:
                    genre, _ = Genre.objects.get_or_create(
                        name=genre_name,
                        defaults={'slug': slugify(genre_name)}
                    )
                    manga.genres.add(genre)
        
        print(f"Manga {slug} successfully saved to DB")
        return manga
        
    except Exception as e:
        print(f"Error fetching manga {slug}: {e}")
        import traceback
        traceback.print_exc()
        return None


def _fetch_and_save_chapters(manga, slug):
    """
    Парсит главы с MangaLib и сохраняет в БД
    
    Args:
        manga: Manga object
        slug: Slug манги
    """
    parser = get_parser('mangalib')
    
    if not parser:
        print("Parser MangaLib not found")
        return
    
    try:
        # Получаем главы с парсера
        chapters_data = parser.get_chapters(slug)
        
        if not chapters_data:
            print(f"No chapters found for {slug}")
            return
        
        # Сохраняем главы в транзакции
        with transaction.atomic():
            created_count = 0
            for chapter_data in chapters_data:
                _, created = Chapter.objects.get_or_create(
                    manga=manga,
                    number=chapter_data['number'],
                    defaults={
                        # Если title равен None, используем пустую строку
                        'title': chapter_data.get('title') or '', 
                        'url': chapter_data.get('url') or '',
                        'volume': chapter_data.get('volume', 1),
                    }
                )
                if created:
                    created_count += 1
            
            # Обновляем количество глав в манге
            manga.total_chapters = manga.chapters.count()
            manga.save(update_fields=['total_chapters'])
            
            print(f"Saved {created_count} chapters for {manga.title}")
        
    except Exception as e:
        print(f"Error fetching chapters for {slug}: {e}")
        import traceback
        traceback.print_exc()