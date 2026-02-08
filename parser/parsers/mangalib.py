#mangalib.py

import aiohttp
import asyncio
from typing import List, Dict, Optional
from .base import BaseParser

class MangaLibParser(BaseParser):
    def __init__(self):
        self.api_url = "https://api.cdnlibs.org/api/manga/"
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

    # --- ПОИСК ---
    def search(self, query: str, limit: int = 20) -> List[Dict]:
        return asyncio.run(self._search_async(query, limit))
    
    async def _search_async(self, query: str, limit: int = 20) -> List[Dict]:
        params = f"q={query}&site_id[]=1&limit={limit}&fields[]=rate_avg&fields[]=rate&fields[]=releaseDate"
        url = f"{self.api_url}?{params}"
        
        async with aiohttp.ClientSession() as session:
            try:
                data = await self._fetch(session, url)
                return self._parse_search_results(data)
            except Exception as e:
                print(f"Search error: {e}")
                return []

    def _parse_search_results(self, data: dict) -> List[Dict]:
        results = []
        if 'data' not in data: 
            return results
        
        for item in data['data']:
            results.append({
                'title': item.get('rus_name') or item.get('name'),
                'slug': item.get('slug_url'),
                'cover_url': item.get('cover', {}).get('default', ''),
                'description': item.get('summary', ''),
                'source': 'mangalib',
                'content_type': self._get_content_type(item.get('type', {}).get('label')),
                'year': item.get('releaseDate'),
                'rating': item.get('rate_avg'),
                'original_url': f"https://mangalib.org/{item.get('slug_url')}"
            })
        return results

    # --- ДЕТАЛИ ---
    def get_manga_details(self, slug: str) -> Optional[Dict]:
        return asyncio.run(self._get_manga_details_async(slug))
    
    async def _get_manga_details_async(self, slug: str) -> Optional[Dict]:
        params = "?fields[]=background&fields[]=eng_name&fields[]=otherNames&fields[]=summary&fields[]=releaseDate&fields[]=type_id&fields[]=caution&fields[]=views&fields[]=close_view&fields[]=rate_avg&fields[]=rate&fields[]=genres&fields[]=tags&fields[]=teams&fields[]=user&fields[]=franchise&fields[]=authors&fields[]=publisher&fields[]=userRating&fields[]=moderated&fields[]=metadata&fields[]=metadata.count&fields[]=metadata.close_comments&fields[]=manga_status_id&fields[]=chap_count&fields[]=status_id&fields[]=artists&fields[]=format"
        url = f"{self.api_url}{slug}{params}"
        
        async with aiohttp.ClientSession() as session:
            try:
                data = await self._fetch(session, url)
                return self._parse_manga_details(data)
            except Exception as e:
                print(f"Details error: {e}")
                return None

    def _parse_manga_details(self, data: dict) -> Dict:
        manga_data = data.get('data', {})
        return {
            'title': manga_data.get('rus_name') or manga_data.get('name'),
            'slug': manga_data.get('slug_url'),
            'cover_url': manga_data.get('cover', {}).get('default', ''),
            'description': manga_data.get('summary') or manga_data.get('description') or 'Описание отсутствует',
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

    # --- ГЛАВЫ И СТРАНИЦЫ ---
    def get_chapters(self, slug: str) -> List[Dict]:
        return asyncio.run(self._get_chapters_async(slug))
    
    async def _get_chapters_async(self, slug: str) -> List[Dict]:
        url = f"{self.api_url}{slug}/chapters"
        async with aiohttp.ClientSession() as session:
            try:
                data = await self._fetch(session, url)
                return self._parse_chapters(data, slug)
            except Exception as e:
                print(f"Chapters error: {e}")
                return []

    def _parse_chapters(self, data: dict, slug: str) -> List[Dict]:
        chapters = []
        if 'data' not in data: 
            return chapters
        for chapter in data['data']:
            chapters.append({
                'number': chapter.get('number'),
                'volume': chapter.get('volume', 0),
                'title': chapter.get('name', ''),
                'url': f"https://mangalib.org/{slug}/v{chapter.get('volume')}/c{chapter.get('number')}",
            })
        return chapters

    def get_pages(self, slug: str, volume: int, number: str) -> List[str]:
        """Синхронный метод для использования в Django views"""
        def get_pages(self, **kwargs) -> List[str]:
            slug = kwargs.get('manga_slug')
            volume = kwargs.get('volume')
            number = kwargs.get('number')
            return asyncio.run(self.get_chapter_pages_async(slug, volume, number))

    async def get_chapter_pages_async(self, slug: str, volume: int, number: str) -> List[str]:
        """Получает список URL всех страниц главы"""
        
        try:
            n = float(number)
            clean_number = str(int(n)) if n == int(n) else str(n)
        except (ValueError, TypeError):
            clean_number = str(number)


        url = f"{self.api_url}{slug}/chapter?number={clean_number}&volume={volume}"
        #print(url)
        async with aiohttp.ClientSession() as session:
            try:
                data = await self._fetch(session, url)

                raw_pages = data.get('data', {}).get('pages', []) if isinstance(data.get('data'), dict) else []
                
                clean_urls = []
                for p in raw_pages:
                    img_path = p.get('url')
                    if img_path:
                        clean_urls.append(f"https://img2.imglib.info{img_path}")

                #print(clean_urls)
                return clean_urls
                
            except Exception as e:
                print(f"Pages error: {e}")
                return []

    def _get_content_type(self, type_label: str) -> str:
        mapping = {'Манга': 'Manga', 'Манхва': 'Manhwa', 'Маньхуа': 'Manhua', 'Комикс': 'Comic'}
        return mapping.get(type_label, 'Manga')