# manga/views.py
from django.shortcuts import render, get_object_or_404
from django.http import Http404, HttpResponse, JsonResponse
from manga.models import Manga, Chapter, Genre
from parser.parsers import get_parser, PARSERS
from django.utils.text import slugify
from django.db import transaction
from users.models import ReadingProgress, Bookmark
import io
import zipfile
import requests
import logging

logger = logging.getLogger(__name__)


def get_manga_source(slug: str) -> str:
    """
    Определяет источник манги по slug.
    Сначала проверяет БД, затем пробует все парсеры.
    """
    # Проверяем в БД
    manga = Manga.objects.filter(slug=slug).first()
    if manga and hasattr(manga, 'source'):
        return manga.source
    
    # Пробуем найти через парсеры
    for source_key in PARSERS.keys():
        parser = get_parser(source_key)
        if parser:
            try:
                details = parser.get_manga_details(slug)
                if details:
                    return source_key
            except Exception:
                continue
    
    # По умолчанию - senkuro (как основной)
    return 'senkuro'


def auto_parser(slug: str):
    """Автоматически получает нужный парсер для манги"""
    source = get_manga_source(slug)
    return get_parser(source)


def home(request):
    """Главная страница: показывает историю пользователя и последние обновления"""
    updated_mangas = Manga.objects.all().order_by('-updated_at')[:20]
    
    user_history = []
    if request.user.is_authenticated:
        user_history = ReadingProgress.objects.filter(user=request.user)\
            .select_related('manga')\
            .order_by('-updated_at')[:10]
    
    return render(request, 'manga/home.html', {
        'updated_mangas': updated_mangas,
        'user_history': user_history,
    })


def search(request):
    """Поиск по всем сайтам"""
    query = request.GET.get('q', '').strip()
    source = request.GET.get('source', 'all')  # Можно указать конкретный источник
    
    if not query:
        return render(request, 'manga/search.html', {
            'query': '',
            'search_results': [],
            'sources': list(PARSERS.keys())
        })
    
    search_results = []
    
    # Если указан конкретный источник
    if source != 'all' and source in PARSERS:
        parsers_to_search = {source: PARSERS[source]}
    else:
        parsers_to_search = PARSERS
    
    for source_key, parser_class in parsers_to_search.items():
        parser = parser_class()
        try:
            mangas = parser.search(query, limit=10)
            # Добавляем source к каждой манге
            for manga in mangas:
                manga['source'] = source_key
            
            search_results.append({
                'source_key': source_key,
                'source_name': source_key.capitalize(),
                'mangas': mangas
            })
        except Exception as e:
            print(f"Error searching {source_key}: {e}")
            search_results.append({
                'source_key': source_key,
                'source_name': source_key.capitalize(),
                'mangas': []
            })
    
    return render(request, 'manga/search.html', {
        'query': query,
        'search_results': search_results,
        'sources': list(PARSERS.keys()),
        'selected_source': source
    })


def api_search(request):
    """API для live поиска"""
    query = request.GET.get('q', '').strip()
    source = request.GET.get('source', 'senkuro')
    
    if len(query) < 2:
        return JsonResponse({'results': []})
    
    parser = get_parser(source)
    
    if parser:
        try:
            results = parser.search(query, limit=10)
            # Добавляем source к результатам
            for result in results:
                result['source'] = source
            return JsonResponse({'results': results})
        except Exception as e:
            print(f"API search error: {e}")
            return JsonResponse({'results': [], 'error': str(e)})
    
    return JsonResponse({'results': []})


def manga_detail(request, slug, source=None):
    """
    Страница деталей манги
    source - опциональный параметр, если не указан - определяется автоматически
    """
    print(f"[DEBUG] Запрос манги: slug={slug}, source={source}")
    
    manga = Manga.objects.filter(slug=slug).first()
    
    current_status = None
    last_read_chapter_id = None

    # Если манга не найдена в БД
    if not manga:
        print("[DEBUG] Манга не найдена в БД, загружаем с сайта...")
        
        # Если source не указан, определяем автоматически
        if not source:
            source = get_manga_source(slug)
            print(f"[DEBUG] Автоматически определен источник: {source}")
        
        manga = _fetch_and_save_manga(slug, source)
    else:
        print(f"[DEBUG] Манга найдена в БД: {manga.title}")
        # Если source не указан, берем из БД
        if not source and hasattr(manga, 'source'):
            source = manga.source
    
    if not manga:
        print(f"[ERROR] Не удалось загрузить мангу: {slug}")
        raise Http404("Манга не найдена")

    # Работа с пользователем
    if request.user.is_authenticated:
        bookmark = Bookmark.objects.filter(user=request.user, manga=manga).first()
        if bookmark:
            current_status = bookmark.status
        
        progress = ReadingProgress.objects.filter(
            user=request.user, 
            manga=manga
        ).select_related('last_chapter').first()
        
        if progress and progress.last_chapter:
            last_read_chapter_id = progress.last_chapter.id
            last_read_number = progress.last_chapter.number
        else:
            last_read_number = 0
    else:
        last_read_number = 0
        
    chapters = manga.chapters.all().order_by('number')
    
    # Если глав нет, загружаем
    if not chapters.exists():
        print("[DEBUG] Главы не найдены, загружаем с сайта...")
        _fetch_and_save_chapters(manga, slug, source or 'senkuro')
        chapters = manga.chapters.all().order_by('number')
        print(f"[DEBUG] Загружено глав: {chapters.count()}")
    
    return render(request, 'manga/detail.html', {
        'manga': manga,
        'chapters': chapters,
        'current_status': current_status,
        'last_read_chapter_id': last_read_chapter_id,
        'last_read_number': last_read_number,
        'source': source or 'unknown',
    })


def chapter_reader(request, slug, volume, number, source=None):
    """
    Читалка главы
    source - опциональный параметр
    """
    try:
        num_float = float(number)
    except ValueError:
        raise Http404("Неверный формат номера главы")

    # Ищем главу в БД
    chapter = get_object_or_404(
        Chapter.objects.select_related('manga'), 
        manga__slug=slug, 
        volume=volume, 
        number=num_float
    )
    
    manga = chapter.manga
    
    # Определяем источник
    if not source:
        if hasattr(manga, 'source'):
            source = manga.source
        else:
            source = get_manga_source(slug)
    
    print(f"[DEBUG] Читаем главу из источника: {source}")
    
    # Получаем парсер
    parser = get_parser(source)
    if not parser:
        raise Http404(f"Парсер '{source}' не найден")
    
    parser_kwargs = {
        'manga_slug': manga.slug,
        'volume': chapter.volume,
        'number': chapter.number,
        'chapter_slug': chapter.url
    }
    
    pages = parser.get_pages(**parser_kwargs)
    #print(pages)
    # Сохранение прогресса
    if request.user.is_authenticated:
        ReadingProgress.objects.update_or_create(
            user=request.user,
            manga=manga,
            defaults={'last_chapter': chapter}
        )
    
    # Соседние главы
    prev_chapter = Chapter.objects.filter(
        manga=manga, 
        number__lt=chapter.number
    ).order_by('-number').first()
    
    next_chapter = Chapter.objects.filter(
        manga=manga, 
        number__gt=chapter.number
    ).order_by('number').first()
    
    return render(request, 'manga/reader.html', {
        'chapter': chapter,
        'manga': manga,
        'pages': pages,
        'prev_chapter': prev_chapter,
        'next_chapter': next_chapter,
        'source': source,
    })


def download_chapter_zip(request, slug, volume, number, source=None):
    """Скачивает все страницы главы и отдает ZIP-архив"""
    
    # Определяем источник
    if not source:
        source = get_manga_source(slug)
    
    parser = get_parser(source)
    if not parser:
        return HttpResponse(f"Парсер '{source}' не найден", status=404)
    
    # Получаем прямые ссылки на картинки
    chapter = get_object_or_404(Chapter, manga__slug=slug, volume=volume, number=number)
    pages = parser.get_pages(
        manga_slug=slug, 
        volume=volume, 
        number=number, 
        chapter_slug=chapter.url
    )
    
    if not pages:
        return HttpResponse("Не удалось получить страницы главы", status=404)

    # Создаем архив в памяти
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as zip_file:
        for i, page_url in enumerate(pages, 1):
            try:
                response = requests.get(page_url, timeout=10)
                if response.status_code == 200:
                    ext = page_url.split('.')[-1].split('?')[0] or 'jpg'
                    filename = f"page_{i:03d}.{ext}"
                    zip_file.writestr(filename, response.content)
            except Exception as e:
                print(f"Error downloading page {page_url}: {e}")

    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type='application/zip')
    response['Content-Disposition'] = f'attachment; filename="{slug}_v{volume}_c{number}.zip"'
    return response


def _fetch_and_save_manga(slug: str, source: str = 'senkuro'):
    """
    Парсит мангу и сохраняет в БД
    source - источник данных (senkuro, mangalib и т.д.)
    """
    print(f"[DEBUG] Загрузка манги: {slug} из {source}")
    
    parser = get_parser(source)
    
    if not parser:
        print(f"[ERROR] Парсер '{source}' не найден")
        return None
    
    try:
        print(f"[DEBUG] Получаем детали манги с {source}...")
        details = parser.get_manga_details(slug)
        
        if not details:
            print(f"[ERROR] API вернул пустые детали для {slug}")
            return None
        
        print(f"[DEBUG] Получены детали: {details.get('title', 'NO TITLE')}")
        
        with transaction.atomic():
            # Создаем мангу с указанием источника
            manga_data = {
                'title': details['title'],
                'slug': slug,
                'description': details.get('description', ''),
                'cover_url': details.get('cover_url', ''),
                'original_url': details.get('original_url', ''),
                'author': details.get('author', ''),
                'artist': details.get('artist', ''),
                'year': details.get('year'),
                'total_chapters': details.get('total_chapters', 0),
            }
            
            # Добавляем source если модель поддерживает
            # (нужно добавить поле source в модель Manga)
            # manga_data['source'] = source
            
            manga = Manga.objects.create(**manga_data)
            
            print(f"[DEBUG] Манга создана в БД: {manga.title}")
            
            # Добавляем жанры
            if details.get('genres'):
                for genre_name in details['genres']:
                    genre, _ = Genre.objects.get_or_create(
                        name=genre_name,
                        defaults={
                            'slug': slugify(genre_name, allow_unicode=True) 
                                   or f"genre-{genre_name[:10]}"
                        }
                    )
                    manga.genres.add(genre)
                print(f"[DEBUG] Добавлено жанров: {len(details['genres'])}")
        
        return manga
        
    except Exception as e:
        print(f"[ERROR] Ошибка при загрузке манги {slug}: {e}")
        import traceback
        traceback.print_exc()
        return None


def _fetch_and_save_chapters(manga, slug: str, source: str = 'senkuro'):
    """
    Загружает главы с сайта и сохраняет в БД
    source - источник данных
    """
    print(f"[DEBUG] Загрузка глав для: {slug} из {source}")
    
    parser = get_parser(source)
    
    if not parser:
        print(f"[ERROR] Парсер '{source}' не найден")
        return
    
    try:
        print(f"[DEBUG] Получаем список глав с {source}...")
        chapters_data = parser.get_chapters(slug)
        
        if not chapters_data:
            print(f"[WARNING] API вернул пустой список глав для {slug}")
            return
        
        print(f"[DEBUG] Получено глав с API: {len(chapters_data)}")
        
        with transaction.atomic():
            created_count = 0
            for chapter_data in chapters_data:
                chapter, created = Chapter.objects.get_or_create(
                    manga=manga,
                    number=chapter_data['number'],
                    defaults={
                        'title': chapter_data.get('title') or '', 
                        'url': chapter_data.get('url') or '',
                        'volume': chapter_data.get('volume', 1),
                    }
                )
                if created:
                    created_count += 1
            
            print(f"[DEBUG] Создано новых глав: {created_count}")
            
            manga.total_chapters = manga.chapters.count()
            manga.save(update_fields=['total_chapters'])
            print(f"[DEBUG] Всего глав в БД: {manga.total_chapters}")
        
    except Exception as e:
        print(f"[ERROR] Ошибка при загрузке глав для {slug}: {e}")
        import traceback
        traceback.print_exc()