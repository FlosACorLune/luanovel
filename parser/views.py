from django.shortcuts import render
from django.http import JsonResponse
from manga.models import Manga, Chapter, Genre # Убрали ContentType
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
    
    search_results = []
    
    for source_key, parser_class in PARSERS.items():
        parser = parser_class()
        try:
            mangas = parser.search(query, limit=10)
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
        'search_results': search_results
    })


def api_search(request):
    """API для live поиска"""
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
    """Страница деталей манги"""
    manga = Manga.objects.filter(slug=slug).first()
    
    if not manga:
        manga = _fetch_and_save_manga(slug)
    
    if not manga:
        return render(request, 'manga/detail.html', {
            'manga': None,
            'chapters': [],
            'error': 'Манга не найдена'
        })
    
    chapters = manga.chapters.all().order_by('-number')[:100]
    
    if not chapters.exists():
        _fetch_and_save_chapters(manga, slug)
        chapters = manga.chapters.all().order_by('-number')[:100]
    
    return render(request, 'manga/detail.html', {
        'manga': manga,
        'chapters': chapters
    })


def _fetch_and_save_manga(slug):
    """Парсит мангу и сохраняет в БД"""
    parser = get_parser('mangalib')
    
    if not parser:
        return None
    
    try:
        details = parser.get_manga_details(slug)
        if not details:
            return None
        
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
    """Парсит главы и сохраняет в БД"""
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
                        'title': chapter_data.get('title') or '',
                        'url': chapter_data['url'],
                        'volume': chapter_data.get('volume', 1),
                    }
                )
        
        manga.total_chapters = manga.chapters.count()
        manga.save(update_fields=['total_chapters'])
        
    except Exception as e:
        print(f"Error fetching chapters for {slug}: {e}")