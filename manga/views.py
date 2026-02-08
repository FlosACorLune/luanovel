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


def get_source_from_url(url: str) -> str:
    """Определяет source по URL"""
    if not url:
        return 'senkuro'
    
    url_lower = url.lower()
    if 'mangalib.org' in url_lower or 'mangalib.me' in url_lower:
        return 'mangalib'
    elif 'senkuro.me' in url_lower:
        return 'senkuro'
    
    return 'senkuro'


def get_manga_source(slug: str) -> str:
    """Определяет источник манги"""

    manga = Manga.objects.filter(slug=slug).first()
    if manga:
        if manga.source:
            return manga.source
        
        if manga.original_url:
            detected = get_source_from_url(manga.original_url)
            manga.source = detected
            manga.save(update_fields=['source'])
            return detected
    
    for source_key in ['senkuro', 'mangalib']:
        parser = get_parser(source_key)
        if parser:
            try:
                details = parser.get_manga_details(slug)
                if details:
                    return source_key
            except Exception:
                continue
    
    return 'senkuro'


def home(request):
    """Главная страница"""
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
    
    if source != 'all' and source in PARSERS:
        parsers_to_search = {source: PARSERS[source]}
    else:
        parsers_to_search = PARSERS
    
    for source_key, parser_class in parsers_to_search.items():
        parser = parser_class()
        try:
            mangas = parser.search(query, limit=10)
            for manga in mangas:
                manga['source'] = source_key
            
            search_results.append({
                'source_key': source_key,
                'source_name': source_key.capitalize(),
                'mangas': mangas
            })
        except Exception as e:
            logger.error(f"Search error in {source_key}: {e}")
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
            for result in results:
                result['source'] = source
            return JsonResponse({'results': results})
        except Exception as e:
            logger.error(f"API search error in {source}: {e}")
            return JsonResponse({'results': [], 'error': str(e)})
    
    return JsonResponse({'results': []})


def manga_detail(request, slug, source=None):
    """Страница деталей манги"""
    manga = Manga.objects.filter(slug=slug).first()
    
    current_status = None
    last_read_chapter_id = None

    if manga:

        if not source:
            if manga.source:
                source = manga.source
            elif manga.original_url:
                source = get_source_from_url(manga.original_url)
                manga.source = source
                manga.save(update_fields=['source'])
            else:
                source = get_manga_source(slug)
                manga.source = source
                manga.save(update_fields=['source'])

        elif manga.source != source:
            manga.source = source
            manga.save(update_fields=['source'])
    else:

        if not source:
            source = get_manga_source(slug)
        
        manga = _fetch_and_save_manga(slug, source)
    
    if not manga:
        raise Http404("Манга не найдена")
    

    if not source:
        source = manga.source if manga.source else 'senkuro'


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
    
    if not chapters.exists():
        _fetch_and_save_chapters(manga, slug, source)
        chapters = manga.chapters.all().order_by('number')
    
    return render(request, 'manga/detail.html', {
        'manga': manga,
        'chapters': chapters,
        'current_status': current_status,
        'last_read_chapter_id': last_read_chapter_id,
        'last_read_number': last_read_number,
        'source': source,
    })


def chapter_reader(request, slug, volume, number, source=None):
    """Читалка главы"""
    try:
        num_float = float(number)
    except ValueError:
        raise Http404("Неверный формат номера главы")

    chapter = get_object_or_404(
        Chapter.objects.select_related('manga'), 
        manga__slug=slug, 
        volume=volume, 
        number=num_float
    )
    
    manga = chapter.manga
    

    if not source:
        if manga.source:
            source = manga.source
        elif manga.original_url:
            source = get_source_from_url(manga.original_url)
            manga.source = source
            manga.save(update_fields=['source'])
        else:
            source = get_manga_source(slug)
            manga.source = source
            manga.save(update_fields=['source'])
    
    parser = get_parser(source)
    if not parser:
        raise Http404(f"Парсер '{source}' не найден")
    

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
    
    try:
        pages = parser.get_pages(**parser_kwargs)
    except Exception as e:
        logger.error(f"Error loading pages: {e}")
        pages = []
    

    if request.user.is_authenticated:
        ReadingProgress.objects.update_or_create(
            user=request.user,
            manga=manga,
            defaults={'last_chapter': chapter}
        )
    

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
    
    if not source:
        source = get_manga_source(slug)
    
    parser = get_parser(source)
    if not parser:
        return HttpResponse(f"Парсер '{source}' не найден", status=404)
    
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
                logger.error(f"Error downloading page {page_url}: {e}")

    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type='application/zip')
    response['Content-Disposition'] = f'attachment; filename="{slug}_v{volume}_c{number}.zip"'
    return response


def _fetch_and_save_manga(slug: str, source: str = 'senkuro'):
    """Парсит мангу и сохраняет в БД"""
    parser = get_parser(source)
    
    if not parser:
        return None
    
    try:
        details = parser.get_manga_details(slug)
        
        if not details:
            return None
        
        with transaction.atomic():
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
                'source': source,
            }
            
            manga = Manga.objects.create(**manga_data)
            
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
        
        return manga
        
    except Exception as e:
        logger.error(f"Error fetching manga {slug}: {e}")
        return None


def _fetch_and_save_chapters(manga, slug: str, source: str = 'senkuro'):
    """Загружает главы с сайта и сохраняет в БД"""
    parser = get_parser(source)
    
    if not parser:
        return
    
    try:
        chapters_data = parser.get_chapters(slug)
        
        if not chapters_data:
            return
        
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
            
            manga.total_chapters = manga.chapters.count()
            manga.save(update_fields=['total_chapters'])
        
    except Exception as e:
        logger.error(f"Error fetching chapters for {slug}: {e}")