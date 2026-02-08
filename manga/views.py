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
    if manga and manga.source:
        logger.info(f"Источник найден в БД: {manga.source} для {slug}")
        return manga.source
    
    # Пробуем найти через парсеры
    # Приоритет: сначала senkuro (работает), потом остальные
    priority_sources = ['senkuro', 'mangalib']
    other_sources = [s for s in PARSERS.keys() if s not in priority_sources]
    all_sources = priority_sources + other_sources
    
    for source_key in all_sources:
        parser = get_parser(source_key)
        if parser:
            try:
                logger.info(f"Пробуем источник {source_key} для {slug}")
                details = parser.get_manga_details(slug)
                if details:
                    logger.info(f"Манга найдена в {source_key}: {details.get('title')}")
                    return source_key
            except Exception as e:
                logger.debug(f"Источник {source_key} не подошёл: {e}")
                continue
    
    # По умолчанию - senkuro (работающий источник)
    logger.warning(f"Источник не определён для {slug}, используем senkuro по умолчанию")
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
    source = request.GET.get('source', 'all')
    
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
            logger.info(f"Поиск '{query}' в {source_key}")
            mangas = parser.search(query, limit=10)
            
            # Добавляем source к каждой манге
            for manga in mangas:
                manga['source'] = source_key
            
            search_results.append({
                'source_key': source_key,
                'source_name': source_key.capitalize(),
                'mangas': mangas
            })
            logger.info(f"Найдено в {source_key}: {len(mangas)} результатов")
        except Exception as e:
            logger.error(f"Ошибка поиска в {source_key}: {e}")
            search_results.append({
                'source_key': source_key,
                'source_name': source_key.capitalize(),
                'mangas': [],
                'error': str(e)
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
            logger.error(f"API search error in {source}: {e}")
            return JsonResponse({'results': [], 'error': str(e)})
    
    return JsonResponse({'results': []})


def manga_detail(request, slug, source=None):
    """
    Страница деталей манги
    source - опциональный параметр из URL, если не указан - определяется автоматически
    """
    logger.info(f"[manga_detail] Запрос: slug={slug}, source={source}")
    
    # Проверяем БД
    manga = Manga.objects.filter(slug=slug).first()
    
    current_status = None
    last_read_chapter_id = None

    # Если манга найдена в БД
    if manga:
        logger.info(f"Манга найдена в БД: {manga.title}")
        
        # Если source не указан в URL, берём из БД
        if not source and manga.source:
            source = manga.source
            logger.info(f"Источник взят из БД: {source}")
        # Если source указан в URL, но отличается от БД - обновляем
        elif source and manga.source != source:
            logger.warning(f"Источник в URL ({source}) отличается от БД ({manga.source})")
            manga.source = source
            manga.save(update_fields=['source'])
    
    # Если манга не найдена в БД - загружаем
    else:
        logger.info("Манга не найдена в БД, загружаем...")
        
        # Определяем источник если не указан
        if not source:
            source = get_manga_source(slug)
            logger.info(f"Автоматически определён источник: {source}")
        
        manga = _fetch_and_save_manga(slug, source)
    
    # Если всё равно не удалось загрузить
    if not manga:
        logger.error(f"Не удалось загрузить мангу: {slug}")
        raise Http404("Манга не найдена")
    
    # Убеждаемся что source определён
    if not source:
        if manga.source:
            source = manga.source
        else:
            source = get_manga_source(slug)
            manga.source = source
            manga.save(update_fields=['source'])
    
    logger.info(f"Итоговый источник: {source}")

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
        logger.info("Главы не найдены, загружаем с сайта...")
        _fetch_and_save_chapters(manga, slug, source)
        chapters = manga.chapters.all().order_by('number')
        logger.info(f"Загружено глав: {chapters.count()}")
    
    return render(request, 'manga/detail.html', {
        'manga': manga,
        'chapters': chapters,
        'current_status': current_status,
        'last_read_chapter_id': last_read_chapter_id,
        'last_read_number': last_read_number,
        'source': source,
    })


def chapter_reader(request, slug, volume, number, source=None):
    """
    Читалка главы
    source - опциональный параметр из URL
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
        if manga.source:
            source = manga.source
        else:
            source = get_manga_source(slug)
            manga.source = source
            manga.save(update_fields=['source'])
    
    logger.info(f"[chapter_reader] Читаем главу из источника: {source}")
    
    # Получаем парсер
    parser = get_parser(source)
    if not parser:
        raise Http404(f"Парсер '{source}' не найден")
    
    # Подготовка kwargs в зависимости от источника
    if source == 'senkuro':
        # Для senkuro используем chapter_slug
        parser_kwargs = {
            'chapter_slug': chapter.url
        }
    elif source == 'mangalib':
        # Для mangalib используем manga_slug, volume, number
        parser_kwargs = {
            'manga_slug': slug,
            'volume': volume,
            'number': str(number)
        }
    else:
        # Универсальный вариант - передаём всё
        parser_kwargs = {
            'manga_slug': slug,
            'volume': volume,
            'number': str(number),
            'chapter_slug': chapter.url
        }
    
    try:
        pages = parser.get_pages(**parser_kwargs)
        logger.info(f"Загружено страниц: {len(pages)}")
    except Exception as e:
        logger.error(f"Ошибка загрузки страниц: {e}")
        pages = []
    
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
    """Скачивает все страницы главы и отдаёт ZIP-архив"""
    
    # Определяем источник
    if not source:
        source = get_manga_source(slug)
    
    parser = get_parser(source)
    if not parser:
        return HttpResponse(f"Парсер '{source}' не найден", status=404)
    
    # Получаем главу
    try:
        num_float = float(number)
    except ValueError:
        return HttpResponse("Неверный формат номера главы", status=400)
    
    chapter = get_object_or_404(
        Chapter, 
        manga__slug=slug, 
        volume=volume, 
        number=num_float
    )
    
    # Получаем страницы в зависимости от источника
    if source == 'senkuro':
        parser_kwargs = {'chapter_slug': chapter.url}
    elif source == 'mangalib':
        parser_kwargs = {
            'manga_slug': slug,
            'volume': volume,
            'number': str(number)
        }
    else:
        parser_kwargs = {
            'manga_slug': slug,
            'volume': volume,
            'number': str(number),
            'chapter_slug': chapter.url
        }
    
    pages = parser.get_pages(**parser_kwargs)
    
    if not pages:
        return HttpResponse("Не удалось получить страницы главы", status=404)

    # Создаём архив в памяти
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
                logger.error(f"Ошибка загрузки страницы {page_url}: {e}")

    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type='application/zip')
    response['Content-Disposition'] = f'attachment; filename="{slug}_v{volume}_c{number}.zip"'
    return response


def _fetch_and_save_manga(slug: str, source: str = 'senkuro'):
    """
    Парсит мангу и сохраняет в БД
    source - источник данных (senkuro, mangalib и т.д.)
    """
    logger.info(f"[_fetch_and_save_manga] Загрузка: {slug} из {source}")
    
    parser = get_parser(source)
    
    if not parser:
        logger.error(f"Парсер '{source}' не найден")
        return None
    
    try:
        logger.info(f"Получаем детали манги с {source}...")
        details = parser.get_manga_details(slug)
        
        if not details:
            logger.error(f"API вернул пустые детали для {slug}")
            return None
        
        logger.info(f"Получены детали: {details.get('title', 'NO TITLE')}")
        
        with transaction.atomic():
            # Создаём мангу с указанием источника
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
                'source': source,  # Добавляем источник
            }
            
            logger.info(f"Сохраняем источник в БД: {source}")
            
            manga = Manga.objects.create(**manga_data)
            
            logger.info(f"Манга создана в БД: {manga.title}")
            
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
                logger.info(f"Добавлено жанров: {len(details['genres'])}")
        
        return manga
        
    except Exception as e:
        logger.error(f"Ошибка при загрузке манги {slug}: {e}")
        import traceback
        traceback.print_exc()
        return None


def _fetch_and_save_chapters(manga, slug: str, source: str = 'senkuro'):
    """
    Загружает главы с сайта и сохраняет в БД
    source - источник данных
    """
    logger.info(f"[_fetch_and_save_chapters] Загрузка глав: {slug} из {source}")
    
    parser = get_parser(source)
    
    if not parser:
        logger.error(f"Парсер '{source}' не найден")
        return
    
    try:
        logger.info(f"Получаем список глав с {source}...")
        chapters_data = parser.get_chapters(slug)
        
        if not chapters_data:
            logger.warning(f"API вернул пустой список глав для {slug}")
            return
        
        logger.info(f"Получено глав с API: {len(chapters_data)}")
        
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
            
            logger.info(f"Создано новых глав: {created_count}")
            
            manga.total_chapters = manga.chapters.count()
            manga.save(update_fields=['total_chapters'])
            logger.info(f"Всего глав в БД: {manga.total_chapters}")
        
    except Exception as e:
        logger.error(f"Ошибка при загрузке глав для {slug}: {e}")
        import traceback
        traceback.print_exc()