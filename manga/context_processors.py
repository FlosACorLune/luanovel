def manga_sources(request):
    """
    Добавляет список источников манги во все шаблоны
    """
    sources = [
        {
            'key': 'senkuro',
            'name': 'Senkuro',
            'icon': 'manga/icons/senkuro.com.ico',
            'url': 'https://senkuro.com'
        },
        {
            'key': 'mangalib',
            'name': 'MangaLib',
            'icon': 'manga/icons/mangalib.org.png',
            'url': 'https://mangalib.org'
        },
    ]
    
    current_source = request.GET.get('source', 'all')
    
    return {
        'manga_sources': sources,
        'current_source': current_source
    }
    
    '''
        {
            'key': 'mangahub',
            'name': 'MangaHub',
            'icon': 'manga/icons/mangahub.cc.png',
            'url': 'https://mangahub.cc'
        },
        {
            'key': 'mangabuff',
            'name': 'MangaBuff',
            'icon': 'manga/icons/mangabuff.ru.ico',
            'url': 'https://mangabuff.ru'
        },
    '''