from django.shortcuts import render
from manga.models import Manga

def home(request):
    """Главная страница"""
    source = request.GET.get('source', 'all')
    
    # Показываем манги из БД (если есть)
    mangas = Manga.objects.all().select_related('content_type')[:20]
    
    return render(request, 'manga/home.html', {
        'mangas': mangas,
    })

def manga_detail(request, slug):
    """Страница деталей манги"""
    # Пока заглушка
    return render(request, 'manga/detail.html', {
        'manga': None
    })