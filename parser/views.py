from django.shortcuts import render
from django.http import JsonResponse
from parser.parsers import get_parser, PARSERS

def search(request):
    """Поиск по всем сайтам"""
    query = request.GET.get('q', '')
    
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
    query = request.GET.get('q', '')
    
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
