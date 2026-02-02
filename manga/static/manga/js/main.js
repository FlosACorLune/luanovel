/**
 * LuaNovel - Main JavaScript
 * Оптимизированная версия с улучшенной производительностью
 */

(function() {
    'use strict';
    
    // ========== LIVE ПОИСК ==========
    const searchInput = document.getElementById('search-input');
    const searchResults = document.getElementById('live-search-results');
    let searchTimeout = null;
    let currentRequest = null;
    
    if (searchInput && searchResults) {
        // Debounced поиск
        searchInput.addEventListener('input', handleSearchInput);
        
        // Закрыть результаты при клике вне
        document.addEventListener('click', handleClickOutside);
        
        // Клавиатурная навигация
        searchInput.addEventListener('keydown', handleSearchKeydown);
    }
    
    /**
     * Обработчик ввода в поле поиска
     */
    function handleSearchInput(e) {
        const query = e.target.value.trim();
        
        // Отменить предыдущий таймаут
        clearTimeout(searchTimeout);
        
        // Отменить предыдущий запрос
        if (currentRequest) {
            currentRequest.abort();
            currentRequest = null;
        }
        
        // Очистить результаты если запрос слишком короткий
        if (query.length < 2) {
            hideSearchResults();
            return;
        }
        
        // Показать индикатор загрузки
        showLoadingState();
        
        // Отложенный поиск (debounce)
        searchTimeout = setTimeout(function() {
            performSearch(query);
        }, 300);
    }
    
    /**
     * Выполнить поиск
     */
    function performSearch(query) {
        const controller = new AbortController();
        currentRequest = controller;
        
        fetch('/parser/api/search/?q=' + encodeURIComponent(query), {
            signal: controller.signal
        })
        .then(function(response) {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(function(data) {
            currentRequest = null;
            displaySearchResults(data);
        })
        .catch(function(error) {
            currentRequest = null;
            if (error.name !== 'AbortError') {
                console.error('Search error:', error);
                showErrorState();
            }
        });
    }
    
    /**
     * Отобразить результаты поиска
     */
    function displaySearchResults(data) {
        if (data.results && data.results.length > 0) {
            const html = data.results.map(function(item, index) {
                return '<a href="/manga/' + encodeURIComponent(item.slug) + '/" ' +
                       'class="search-result-item" ' +
                       'role="option" ' +
                       'data-index="' + index + '">' +
                       '<img src="' + escapeHtml(item.cover_url) + '" ' +
                       'alt="' + escapeHtml(item.title) + '" ' +
                       'class="search-result-cover" ' +
                       'loading="lazy">' +
                       '<div class="search-result-info">' +
                       '<h4>' + escapeHtml(item.title) + '</h4>' +
                       '<p>' + escapeHtml(item.source) + ' • ' + 
                       escapeHtml(item.content_type || 'Manga') + '</p>' +
                       '</div>' +
                       '</a>';
            }).join('');
            
            searchResults.innerHTML = html;
            searchResults.classList.add('active');
        } else {
            showNoResultsState();
        }
    }
    
    /**
     * Показать состояние загрузки
     */
    function showLoadingState() {
        searchResults.innerHTML = '<div style="padding: 20px; text-align: center; color: #a0a0a0;">' +
                                  'Поиск...</div>';
        searchResults.classList.add('active');
    }
    
    /**
     * Показать состояние "ничего не найдено"
     */
    function showNoResultsState() {
        searchResults.innerHTML = '<div style="padding: 20px; text-align: center; color: #a0a0a0;">' +
                                  'Ничего не найдено</div>';
        searchResults.classList.add('active');
    }
    
    /**
     * Показать состояние ошибки
     */
    function showErrorState() {
        searchResults.innerHTML = '<div style="padding: 20px; text-align: center; color: #ff6b6b;">' +
                                  'Произошла ошибка. Попробуйте снова.</div>';
        searchResults.classList.add('active');
    }
    
    /**
     * Скрыть результаты поиска
     */
    function hideSearchResults() {
        searchResults.classList.remove('active');
        searchResults.innerHTML = '';
    }
    
    /**
     * Обработка клика вне области поиска
     */
    function handleClickOutside(e) {
        if (!searchInput.contains(e.target) && !searchResults.contains(e.target)) {
            hideSearchResults();
        }
    }
    
    /**
     * Клавиатурная навигация по результатам поиска
     */
    function handleSearchKeydown(e) {
        const items = searchResults.querySelectorAll('.search-result-item');
        
        if (items.length === 0) return;
        
        let currentIndex = -1;
        const focusedItem = document.activeElement;
        
        if (focusedItem.classList.contains('search-result-item')) {
            currentIndex = parseInt(focusedItem.dataset.index);
        }
        
        if (e.key === 'ArrowDown') {
            e.preventDefault();
            const nextIndex = Math.min(currentIndex + 1, items.length - 1);
            items[nextIndex].focus();
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            if (currentIndex <= 0) {
                searchInput.focus();
            } else {
                items[currentIndex - 1].focus();
            }
        } else if (e.key === 'Escape') {
            hideSearchResults();
            searchInput.blur();
        }
    }
    
    /**
     * Экранирование HTML для предотвращения XSS
     */
    function escapeHtml(text) {
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        return String(text).replace(/[&<>"']/g, function(m) { return map[m]; });
    }
    
    // ========== LAZY LOADING ИЗОБРАЖЕНИЙ ==========
    if ('IntersectionObserver' in window) {
        const imageObserver = new IntersectionObserver(function(entries, observer) {
            entries.forEach(function(entry) {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    if (img.dataset.src) {
                        img.src = img.dataset.src;
                        img.removeAttribute('data-src');
                    }
                    img.classList.add('loaded');
                    observer.unobserve(img);
                }
            });
        }, {
            rootMargin: '50px'
        });
        
        // Наблюдать за всеми изображениями с атрибутом loading="lazy"
        document.addEventListener('DOMContentLoaded', function() {
            document.querySelectorAll('img[loading="lazy"]').forEach(function(img) {
                imageObserver.observe(img);
            });
        });
    }
    
    // ========== СОХРАНЕНИЕ ПОЗИЦИИ ПРОКРУТКИ ==========
    window.addEventListener('beforeunload', function() {
        const scrollPos = window.scrollY;
        sessionStorage.setItem('scrollPosition', scrollPos);
    });
    
    window.addEventListener('load', function() {
        const scrollPos = sessionStorage.getItem('scrollPosition');
        if (scrollPos) {
            window.scrollTo(0, parseInt(scrollPos));
            sessionStorage.removeItem('scrollPosition');
        }
    });
    
})();