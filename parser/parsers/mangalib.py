import aiohttp
import asyncio
from typing import List, Dict, Optional
from .base import BaseParser

class MangaLibParser(BaseParser):
    def __init__(self):
        self.api_url = "https://api.cdnlibs.org/api/manga/"
        self.search_url = "https://api.cdnlibs.org/api/manga"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Content-Type": "application/json",
            "Origin": "https://mangalib.org",
            "Referer": "https://mangalib.org/",
            "Site-Id": "1",
        }
    
    async def _fetch(self, session: aiohttp.ClientSession, url: str) -> dict:
        """Асинхронный запрос"""
        async with session.get(url, headers=self.headers, timeout=10) as response:
            response.raise_for_status()
            return await response.json()
    
    def search(self, query: str, limit: int = 20) -> List[Dict]:
        """Синхронная обёртка для поиска"""
        return asyncio.run(self._search_async(query, limit))
    
    async def _search_async(self, query: str, limit: int = 20) -> List[Dict]:
        """Поиск манги"""
        search_params = {
            'q': query,
            'site_id[]': '1',
            'limit': limit,
            'fields[]': ['rate_avg', 'rate', 'releaseDate']
        }
        
        # Формируем URL с параметрами
        params_str = f"q={query}&site_id[]=1&limit={limit}"
        params_str += "&fields[]=rate_avg&fields[]=rate&fields[]=releaseDate"
        url = f"{self.search_url}?{params_str}"
        
        async with aiohttp.ClientSession() as session:
            try:
                data = await self._fetch(session, url)
                return self._parse_search_results(data)
            except Exception as e:
                print(f"Search error: {e}")
                return []
    
    def _parse_search_results(self, data: dict) -> List[Dict]:
        """Парсит результаты поиска"""
        results = []
        
        if 'data' not in data:
            return results
        
        for item in data['data']:
            results.append({
                'title': item.get('rus_name') or item.get('name'),
                'slug': item.get('slug_url'),
                'cover_url': item.get('cover', {}).get('default', ''),
                'description': item.get('summary', '')[:200] + '...' if item.get('summary') else '',
                'source': 'mangalib',
                'content_type': self._get_content_type(item.get('type', {}).get('label')),
                'year': item.get('releaseDate'),
                'rating': item.get('rate_avg'),
                'original_url': f"https://mangalib.org/{item.get('slug_url')}"
            })
        
        return results
    
    def _get_content_type(self, type_label: str) -> str:
        """Определяет тип контента"""
        mapping = {
            'Манга': 'Manga',
            'Манхва': 'Manhwa',
            'Маньхуа': 'Manhua',
            'Комикс': 'Comic',
        }
        return mapping.get(type_label, 'Manga')
    
    def get_manga_details(self, slug: str) -> Optional[Dict]:
        """Синхронная обёртка для получения деталей"""
        return asyncio.run(self._get_manga_details_async(slug))
    
    async def _get_manga_details_async(self, slug: str) -> Optional[Dict]:
        """Получить полную информацию о манге"""
        params = "?fields[]=background&fields[]=moderated&fields[]=manga_status_id&fields[]=chap_count&fields[]=status_id"
        url = f"{self.api_url}{slug}{params}"
        
        async with aiohttp.ClientSession() as session:
            try:
                data = await self._fetch(session, url)
                return self._parse_manga_details(data)
            except Exception as e:
                print(f"Details error: {e}")
                return None
    
    def _parse_manga_details(self, data: dict) -> Dict:
        """Парсит детали манги"""
        manga_data = data.get('data', {})
        
        return {
            'title': manga_data.get('rus_name') or manga_data.get('name'),
            'slug': manga_data.get('slug_url'),
            'cover_url': manga_data.get('cover', {}).get('default', ''),
            'description': manga_data.get('summary', ''),
            'source': 'mangalib',
            'content_type': self._get_content_type(manga_data.get('type', {}).get('label')),
            'author': ', '.join([a['name'] for a in manga_data.get('authors', [])]),
            'artist': ', '.join([a['name'] for a in manga_data.get('artists', [])]),
            'year': manga_data.get('releaseDate'),
            'status': manga_data.get('status', {}).get('label'),
            'genres': [g['name'] for g in manga_data.get('genres', [])],
            'rating': manga_data.get('rating', {}).get('average'),
            'views': manga_data.get('views', {}).get('total', 0),
            'total_chapters': manga_data.get('items_count', {}).get('uploaded', 0),
            'original_url': f"https://mangalib.org/{manga_data.get('slug_url')}"
        }
    
    def get_chapters(self, slug: str) -> List[Dict]:
        """Синхронная обёртка для получения глав"""
        return asyncio.run(self._get_chapters_async(slug))
    
    async def _get_chapters_async(self, slug: str) -> List[Dict]:
        """Получить список глав"""
        url = f"{self.api_url}{slug}/chapters"
        
        async with aiohttp.ClientSession() as session:
            try:
                data = await self._fetch(session, url)
                return self._parse_chapters(data, slug)
            except Exception as e:
                print(f"Chapters error: {e}")
                return []
    
def _parse_chapters(self, data: dict, slug: str) -> List[Dict]:
    """Парсит главы"""
    chapters = []
    
    if 'data' not in data:
        return chapters
    
    for chapter in data['data']:
        # Проверяем доступность главы
        branch = chapter.get('branches', [{}])[0]
        moderation = branch.get('moderation', {})
        
        if moderation.get('label') == 'На модерации':
            continue
        
        chapters.append({
            'number': chapter.get('number'),
            'volume': chapter.get('volume', 0),
            'title': chapter.get('name', ''),
            'url': f"https://mangalib.org/{slug}/v{chapter.get('volume')}/c{chapter.get('number')}",
            'pages_count': 0,  # Можно парсить позже при открытии главы
        })
    
    return chapters