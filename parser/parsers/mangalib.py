# mangalib.py - Синхронная версия для стабильности на Render.com

import requests
from typing import List, Dict, Optional
from .base import BaseParser


class MangaLibParser(BaseParser):
    def __init__(self):
        self.api_url = "https://api.cdnlibs.org/api/manga/"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36 Edg/144.0.0.0",
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Content-Type": "application/json",
            "Origin": "https://mangalib.org",
            "Referer": "https://mangalib.org/",
            "Site-Id": "1",
        }
        self.timeout = 15  # Увеличенный таймаут для стабильности
    
    def _fetch(self, url: str) -> dict:
        """Синхронный запрос к API"""
        try:
            response = requests.get(url, headers=self.headers, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"MangaLib API error: {e}")
            raise

    # --- ПОИСК ---
    def search(self, query: str, limit: int = 20) -> List[Dict]:
        """Поиск манги по запросу"""
        params = f"q={query}&site_id[]=1&limit={limit}&fields[]=rate_avg&fields[]=rate&fields[]=releaseDate"
        url = f"{self.api_url}?{params}"
        
        try:
            data = self._fetch(url)
            return self._parse_search_results(data)
        except Exception as e:
            print(f"MangaLib search error: {e}")
            return []

    def _parse_search_results(self, data: dict) -> List[Dict]:
        """Парсинг результатов поиска"""
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
        """Получить детальную информацию о манге"""
        params = "?fields[]=background&fields[]=eng_name&fields[]=otherNames&fields[]=summary&fields[]=releaseDate&fields[]=type_id&fields[]=caution&fields[]=views&fields[]=close_view&fields[]=rate_avg&fields[]=rate&fields[]=genres&fields[]=tags&fields[]=teams&fields[]=user&fields[]=franchise&fields[]=authors&fields[]=publisher&fields[]=userRating&fields[]=moderated&fields[]=metadata&fields[]=metadata.count&fields[]=metadata.close_comments&fields[]=manga_status_id&fields[]=chap_count&fields[]=status_id&fields[]=artists&fields[]=format"
        url = f"{self.api_url}{slug}{params}"
        
        try:
            data = self._fetch(url)
            return self._parse_manga_details(data)
        except Exception as e:
            print(f"MangaLib details error for {slug}: {e}")
            return None

    def _parse_manga_details(self, data: dict) -> Dict:
        """Парсинг деталей манги"""
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

    # --- ГЛАВЫ ---
    def get_chapters(self, slug: str) -> List[Dict]:
        """Получить список глав манги"""
        url = f"{self.api_url}{slug}/chapters"
        
        try:
            data = self._fetch(url)
            return self._parse_chapters(data, slug)
        except Exception as e:
            print(f"MangaLib chapters error for {slug}: {e}")
            return []

    def _parse_chapters(self, data: dict, slug: str) -> List[Dict]:
        """Парсинг списка глав"""
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

    # --- СТРАНИЦЫ ---
    def get_pages(self, **kwargs) -> List[str]:
        """
        Получить список URL всех страниц главы
        
        Args:
            manga_slug (str): Slug манги
            volume (int): Номер тома
            number (str/float): Номер главы
        
        Returns:
            List[str]: Список URL изображений страниц
        """
        slug = kwargs.get('manga_slug')
        volume = kwargs.get('volume')
        number = kwargs.get('number')
        
        if not all([slug, volume is not None, number is not None]):
            print(f"MangaLib get_pages: недостаточно параметров - slug={slug}, volume={volume}, number={number}")
            return []
        
        try:
            # Нормализация номера главы
            try:
                n = float(number)
                clean_number = str(int(n)) if n == int(n) else str(n)
            except (ValueError, TypeError):
                clean_number = str(number)
            
            url = f"{self.api_url}{slug}/chapter?number={clean_number}&volume={volume}"
            
            data = self._fetch(url)
            
            # Извлечение страниц
            raw_pages = data.get('data', {}).get('pages', []) if isinstance(data.get('data'), dict) else []
            
            clean_urls = []
            for p in raw_pages:
                img_path = p.get('url')
                if img_path:
                    clean_urls.append(f"https://img2.imglib.info{img_path}")
            
            print(f"MangaLib: загружено {len(clean_urls)} страниц для {slug} v{volume} c{clean_number}")
            return clean_urls
            
        except Exception as e:
            print(f"MangaLib pages error: {e}")
            return []

    def _get_content_type(self, type_label: str) -> str:
        """Преобразование типа контента"""
        mapping = {
            'Манга': 'Manga',
            'Манхва': 'Manhwa',
            'Маньхуа': 'Manhua',
            'Комикс': 'Comic'
        }
        return mapping.get(type_label, 'Manga')