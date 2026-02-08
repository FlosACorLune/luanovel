# senkuro.py - Синхронная версия с улучшенной обработкой ошибок

import requests
from typing import List, Dict, Optional
from .base import BaseParser


class SenkuroParser(BaseParser):
    def __init__(self):
        self.api_url = 'https://api.senkuro.me/graphql'
        self.headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
        }
        self.timeout = 15  # Увеличенный таймаут

    def _post_request(self, payload: dict) -> dict:
        """
        Вспомогательный метод для POST-запросов к GraphQL API
        
        Args:
            payload (dict): Payload запроса
            
        Returns:
            dict: JSON-ответ от API
            
        Raises:
            requests.exceptions.RequestException: При ошибке запроса
        """
        try:
            response = requests.post(
                self.api_url, 
                json=payload, 
                headers=self.headers, 
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Senkuro API error: {e}")
            raise

    # --- ПОИСК ---
    def search(self, query: str, limit: int = 20) -> List[Dict]:
        """Поиск манги по запросу"""
        payload = {
            "operationName": "search",
            "variables": {"query": query, "type": "MANGA"},
            "extensions": {
                "persistedQuery": {
                    "version": 1,
                    "sha256Hash": "e64937b4fc9c921c2141f2995473161bed921c75855c5de934752392175936bc"
                }
            }
        }
        
        try:
            data = self._post_request(payload)
            edges = data.get('data', {}).get('search', {}).get('edges', [])
            
            results = []
            for edge in edges[:limit]:
                node = edge.get('node', {})
                results.append({
                    'title': self._get_title(node.get('titles', [])),
                    'slug': node.get('slug', ''),
                    'cover_url': self._get_cover_url(node.get('cover')),
                    'description': node.get('description', ''),
                    'author': self._get_author(node),
                    'year': node.get('releaseYear'),
                    'source': 'senkuro',
                })
            
            return results
            
        except Exception as e:
            print(f"Senkuro search error: {e}")
            return []

    # --- ДЕТАЛИ ---
    def get_manga_details(self, slug: str) -> Optional[Dict]:
        """Получить детальную информацию о манге"""
        payload = {
            "operationName": "fetchManga",
            "variables": {"slug": slug},
            "extensions": {
                "persistedQuery": {
                    "version": 1,
                    "sha256Hash": "6d8b28abb9a9ee3199f6553d8f0a61c005da8f5c56a88ebcf3778eff28d45bd5"
                }
            }
        }
        
        try:
            data = self._post_request(payload)
            manga = data.get('data', {}).get('manga', {})
            
            if not manga:
                print(f"Senkuro: манга {slug} не найдена")
                return None
            
            # Извлечение основной информации
            title = self._get_title(manga.get('titles', []))
            cover_url = self._get_cover_url(manga.get('cover'))
            description = self._get_description(manga.get('localizations', []))
            
            # Жанры
            genres = [
                tag.get('name', '') 
                for tag in manga.get('tags', []) 
                if tag.get('category') == 'GENRE'
            ]
            
            # Автор и художник
            author = ''
            artist = ''
            for staff in manga.get('mainStaff', []):
                roles = staff.get('roles', [])
                person_name = staff.get('person', {}).get('name', '')
                
                if 'STORY' in roles or 'STORY_AND_ART' in roles:
                    author = person_name
                if 'ART' in roles or 'STORY_AND_ART' in roles:
                    artist = person_name
            
            # Количество глав
            branches = manga.get('branches', [])
            total_chapters = branches[0].get('chapters', 0) if branches else 0
            
            return {
                'title': title,
                'slug': slug,
                'description': description,
                'cover_url': cover_url,
                'original_url': f'https://senkuro.me/manga/{slug}',
                'author': author,
                'artist': artist,
                'year': manga.get('releaseYear'),
                'genres': genres,
                'total_chapters': total_chapters,
                'source': 'senkuro',
            }
            
        except Exception as e:
            print(f"Senkuro details error for {slug}: {e}")
            return None

    # --- ГЛАВЫ ---
    def get_chapters(self, slug: str) -> List[Dict]:
        """Получить список глав манги с пагинацией"""
        # Сначала получаем branch_id
        payload_manga = {
            "operationName": "fetchManga",
            "variables": {"slug": slug},
            "extensions": {
                "persistedQuery": {
                    "version": 1,
                    "sha256Hash": "6d8b28abb9a9ee3199f6553d8f0a61c005da8f5c56a88ebcf3778eff28d45bd5"
                }
            }
        }
        
        try:
            res = self._post_request(payload_manga)
            branches = res.get('data', {}).get('manga', {}).get('branches', [])
            
            if not branches:
                print(f"Senkuro: нет веток для {slug}")
                return []
            
            branch_id = branches[0]['id']
            
            # Получаем главы с пагинацией
            all_chapters = []
            after = None
            max_iterations = 100  # Защита от бесконечного цикла
            iteration = 0
            
            while iteration < max_iterations:
                payload = {
                    "operationName": "fetchMangaChapters",
                    "variables": {
                        "after": after,
                        "branchId": branch_id,
                        "orderBy": {"direction": "ASC", "field": "NUMBER"}
                    },
                    "extensions": {
                        "persistedQuery": {
                            "version": 1,
                            "sha256Hash": "8c854e121f05aa93b0c37889e732410df9ea207b4186c965c845a8d970bdcc12"
                        }
                    }
                }
                
                data = self._post_request(payload)
                ch_data = data.get('data', {}).get('mangaChapters', {})
                
                # Добавляем главы из текущей страницы
                for edge in ch_data.get('edges', []):
                    node = edge.get('node', {})
                    all_chapters.append({
                        'number': node.get('number', 0),
                        'volume': node.get('volume', 1),
                        'title': node.get('title', ''),
                        'url': node.get('slug', ''),  # Slug главы для get_pages
                    })
                
                # Проверяем есть ли следующая страница
                page_info = ch_data.get('pageInfo', {})
                if not page_info.get('hasNextPage'):
                    break
                
                after = page_info.get('endCursor')
                iteration += 1
            
            print(f"Senkuro: загружено {len(all_chapters)} глав для {slug}")
            return all_chapters
            
        except Exception as e:
            print(f"Senkuro chapters error for {slug}: {e}")
            return []

    # --- СТРАНИЦЫ ---
    def get_pages(self, **kwargs) -> List[str]:
        """
        Получить список URL всех страниц главы
        
        Args:
            chapter_slug (str): Slug главы (из Chapter.url)
        
        Returns:
            List[str]: Список URL изображений страниц
        """
        chapter_slug = kwargs.get('chapter_slug')
        
        if not chapter_slug:
            print("Senkuro get_pages: chapter_slug не указан")
            return []
        
        payload = {
            "operationName": "fetchMangaChapter",
            "variables": {
                "cdnQuality": "auto",
                "slug": chapter_slug
            },
            "extensions": {
                "persistedQuery": {
                    "version": 1,
                    "sha256Hash": "8e166106650d3659d21e7aadc15e7e59e5def36f1793a9b15287c73a1e27aa50"
                }
            }
        }
        
        try:
            data = self._post_request(payload)
            pages = data.get('data', {}).get('mangaChapter', {}).get('pages', [])
            
            page_urls = [
                p['image']['original']['url'] 
                for p in pages 
                if p.get('image') and p['image'].get('original', {}).get('url')
            ]
            
            print(f"Senkuro: загружено {len(page_urls)} страниц для главы {chapter_slug}")
            return page_urls
            
        except Exception as e:
            print(f"Senkuro pages error for chapter {chapter_slug}: {e}")
            return []

    # --- ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ---
    
    def _get_description(self, localizations: list) -> str:
        """Извлекает и склеивает текст описания из вложенной структуры Tiptap"""
        # Ищем русскую локализацию, если нет — берем первую доступную
        target_loc = next(
            (loc for loc in localizations if loc.get('lang') == 'RU'),
            None
        )
        
        if not target_loc and localizations:
            target_loc = localizations[0]
        
        if not target_loc or not target_loc.get('description'):
            return ""
        
        full_text = []
        # Проходим по всем блокам (параграфам)
        for block in target_loc.get('description', []):
            content = block.get('content', [])
            if content:
                # Внутри блока собираем все текстовые элементы
                paragraph_text = "".join([
                    item.get('text', '') 
                    for item in content 
                    if item.get('type') == 'text'
                ])
                if paragraph_text:
                    full_text.append(paragraph_text)
        
        return "\n".join(full_text).strip()
    
    def _get_title(self, titles: list) -> str:
        """Извлекает название (приоритет русскому)"""
        if not titles:
            return ''
        
        # Ищем русское название
        ru_title = next(
            (t['content'] for t in titles if t.get('lang') == 'RU'),
            None
        )
        
        if ru_title:
            return ru_title
        
        # Если нет русского, берем первое
        return titles[0].get('content', '') if titles else ''
    
    def _get_cover_url(self, cover: dict) -> str:
        """Извлекает URL обложки"""
        if not cover:
            return ''
        
        # Приоритет: original -> medium
        return (
            cover.get('original', {}).get('url') or 
            cover.get('medium', {}).get('url', '')
        )
    
    def _get_author(self, node: dict) -> str:
        """Извлекает автора из данных манги"""
        persons = node.get('persons', [])
        if not persons:
            return ''
        
        # Ищем автора
        author = next(
            (p['name'] for p in persons if p.get('role') == 'AUTHOR'),
            ''
        )
        
        return author