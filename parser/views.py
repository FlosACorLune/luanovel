from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from manga.models import Manga, Chapter, ContentType, Genre
from parser.parsers import get_parser, PARSERS
from django.utils.text import slugify
from django.db import transaction

def search(request):
    """Поиск по всем сайтам"""
    query = request.GET.get('q', '').strip()
    
    if not query:
        return render(request, 'manga/search.html', {
            'query': '',
            'search_results': []
        })
    
    # Собираем результаты со всех источников
    search_results = []
    
    for source_key, parser_class in PARSERS.items():
        parser = parser_class()
        
        try:
            # Поиск по источнику (максимум 10 результатов)
            mangas = parser.search(query, limit=10)
            
            # Добавляем в результаты даже если пусто (чтобы показать "ничего не найдено")
            search_results.append({
                'source_key': source_key,
                'source_name': source_key.capitalize(),  # MangaLib, Senkuro и т.д.
                'mangas': mangas
            })
            
        except Exception as e:
            print(f"Error searching {source_key}: {e}")
            # Добавляем пустой результат при ошибке
            search_results.append({
                'source_key': source_key,
                'source_name': source_key.capitalize(),
                'mangas': []
            })
    
    return render(request, 'manga/search.html', {
        'query': query,
        'search_results': search_results
    })


def api_search(request):
    """API для live поиска (быстрый поиск только по MangaLib)"""
    query = request.GET.get('q', '').strip()
    
    if len(query) < 2:
        return JsonResponse({'results': []})
    
    parser = get_parser('mangalib')
    
    if parser:
        try:
            results = parser.search(query, limit=10)
            return JsonResponse({'results': results})
        except Exception as e:
            print(f"API search error: {e}")
            return JsonResponse({'results': [], 'error': str(e)})
    
    return JsonResponse({'results': []})


def manga_details(request, slug):
    """
    Страница деталей манги
    Если манга не найдена в БД, парсим её с источника
    """
    # Пытаемся найти в базе данных
    manga = Manga.objects.filter(slug=slug).select_related('content_type').first()
    
    # Если не нашли, пробуем спарсить
    if not manga:
        manga = _fetch_and_save_manga(slug)
    
    if not manga:
        return render(request, 'manga/detail.html', {
            'manga': None,
            'chapters': [],
            'error': 'Манга не найдена'
        })
    
    # Получаем главы
    chapters = manga.chapters.all().order_by('-number')[:100]
    
    # Если глав нет, пробуем спарсить
    if not chapters.exists():
        _fetch_and_save_chapters(manga, slug)
        chapters = manga.chapters.all().order_by('-number')[:100]
    
    return render(request, 'manga/detail.html', {
        'manga': manga,
        'chapters': chapters
    })


def _fetch_and_save_manga(slug):
    """
    Парсит мангу с источника и сохраняет в БД
    """
    # Определяем источник по slug (можно улучшить)
    parser = get_parser('mangalib')  # По умолчанию MangaLib
    
    if not parser:
        return None
    
    try:
        # Получаем детали с парсера
        details = parser.get_manga_details(slug)
        
        if not details:
            return None
        
        # Получаем или создаём тип контента
        content_type, _ = ContentType.objects.get_or_create(
            name=details.get('content_type', 'Manga'),
            defaults={
                'default_orientation': 'vertical' if details.get('content_type') in ['Manhwa', 'Manhua'] else 'horizontal'
            }
        )
        
        # Создаём мангу
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
                status='ongoing'  # Можно улучшить маппинг статусов
            )
            
            # Добавляем жанры
            if details.get('genres'):
                for genre_name in details['genres']:
                    genre, _ = Genre.objects.get_or_create(
                        name=genre_name,
                        defaults={'slug': slugify(genre_name)}
                    )
                    manga.genres.add(genre)
        
        return manga
        
    except Exception as e:
        print(f"Error fetching manga {slug}: {e}")
        return None


def _fetch_and_save_chapters(manga, slug):
    """
    Парсит главы с источника и сохраняет в БД
    """
    parser = get_parser('mangalib')
    
    if not parser:
        return
    
    try:
        chapters_data = parser.get_chapters(slug)
        
        with transaction.atomic():
            for chapter_data in chapters_data:
                Chapter.objects.get_or_create(
                    manga=manga,
                    number=chapter_data['number'],
                    defaults={
                        'title': chapter_data.get('title', ''),
                        'url': chapter_data['url'],
                        'pages_count': chapter_data.get('pages_count', 0),
                    }
                )
        
        # Обновляем количество глав в манге
        manga.total_chapters = manga.chapters.count()
        manga.save(update_fields=['total_chapters'])
        
    except Exception as e:
        print(f"Error fetching chapters for {slug}: {e}")