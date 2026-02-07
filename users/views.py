# users/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .forms import UserRegisterForm
from manga.models import Manga
from .models import Bookmark
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User

def register(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Аккаунт создан для {username}! Теперь вы можете войти.')
            return redirect('login')
    else:
        form = UserRegisterForm()
    return render(request, 'users/register.html', {'form': form})

@login_required
def toggle_bookmark(request):
    if request.method == 'POST':
        manga_id = request.POST.get('manga_id')
        status = request.POST.get('status')
        
        manga = get_object_or_404(Manga, id=manga_id)
        
        if status == 'remove':
            Bookmark.objects.filter(user=request.user, manga=manga).delete()
            return JsonResponse({'status': 'success', 'message': 'Удалено из закладок'})
        
        bookmark, created = Bookmark.objects.update_or_create(
            user=request.user, 
            manga=manga,
            defaults={'status': status}
        )
        

        status_display = dict(Bookmark.STATUS_CHOICES).get(status, status)
        return JsonResponse({'status': 'success', 'message': f'Манга в списке "{status_display}"'})
    
    return JsonResponse({'status': 'error', 'message': 'Неверный запрос'}, status=400)

def profile(request, username):

    profile_user = get_object_or_404(User, username=username)
    
    # Получаем его закладки
    bookmarks = profile_user.bookmarks.all().select_related('manga')
    
    # Получаем историю (последние 10 записей)
    history = profile_user.history.all().select_related('manga', 'last_chapter')[:10]

    context = {
        'profile_user': profile_user, # Это тот, чей профиль мы смотрим
        'bookmarks': bookmarks,
        'history': history,
        'is_own_profile': request.user == profile_user # Проверка: мой ли это профиль
    }
    return render(request, 'users/profile.html', context)