// Live поиск
const searchInput = document.getElementById('search-input');
const searchResults = document.getElementById('live-search-results');
let searchTimeout;

if (searchInput) {
    searchInput.addEventListener('input', function() {
        clearTimeout(searchTimeout);
        const query = this.value.trim();
        
        if (query.length < 2) {
            searchResults.classList.remove('active');
            searchResults.innerHTML = '';
            return;
        }
        
        searchTimeout = setTimeout(() => {
            // Изменили URL на правильный
            fetch(`/parser/api/search/?q=${encodeURIComponent(query)}`)
                .then(response => response.json())
                .then(data => {
                    if (data.results && data.results.length > 0) {
                        searchResults.innerHTML = data.results.map(item => `
                            <a href="/parser/details/${item.slug}/" class="search-result-item">
                                <img src="${item.cover_url}" alt="${item.title}" class="search-result-cover">
                                <div class="search-result-info">
                                    <h4>${item.title}</h4>
                                    <p>${item.source} • ${item.content_type || 'Manga'}</p>
                                </div>
                            </a>
                        `).join('');
                        searchResults.classList.add('active');
                    } else {
                        searchResults.innerHTML = '<div style="padding: 20px; text-align: center; color: #a0a0a0;">Ничего не найдено</div>';
                        searchResults.classList.add('active');
                    }
                })
                .catch(error => {
                    console.error('Search error:', error);
                    searchResults.classList.remove('active');
                });
        }, 300);
    });
    
    // Закрыть результаты при клике вне
    document.addEventListener('click', function(e) {
        if (!searchInput.contains(e.target) && !searchResults.contains(e.target)) {
            searchResults.classList.remove('active');
        }
    });
}