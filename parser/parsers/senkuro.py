import requests
from .base import BaseParser

class SenkuroParser(BaseParser):
    def __init__(self):
        self.api_url = 'https://api.senkuro.me/graphql'
        self.headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36...",
        }

    def _post_request(self, payload):
        """Вспомогательный метод для уменьшения повторов"""
        response = requests.post(self.api_url, json=payload, headers=self.headers, timeout=10)
        response.raise_for_status()
        return response.json()

    def search(self, query: str, limit: int = 20) -> list:
        payload = {
            "operationName": "search",
            "variables": {"query": query, "type": "MANGA"},
            "extensions": {"persistedQuery": {"version": 1, "sha256Hash": "e64937b4fc9c921c2141f2995473161bed921c75855c5de934752392175936bc"}}
        }
        try:
            data = self._post_request(payload)
            edges = data.get('data', {}).get('search', {}).get('edges', [])
            return [{
                'title': self._get_title(data.get('titles', [])),
                'slug': (node := edge.get('node', {})).get('slug', ''),
                'cover_url': self._get_cover_url(node.get('cover')),
                'description': node.get('description', ''),
                'author': self._get_author(node),
                'year': node.get('releaseYear'),
            } for edge in edges[:limit]]
        except Exception: return []

    def get_manga_details(self, slug: str) -> dict:
        """Получить детали манги"""
        payload = {
            "operationName": "fetchManga",
            "variables": {
                "slug": slug
            },
            "extensions": {
                "persistedQuery": {
                    "version": 1,
                    "sha256Hash": "6d8b28abb9a9ee3199f6553d8f0a61c005da8f5c56a88ebcf3778eff28d45bd5"
                }
            }
        }
        
        try:
            response = requests.post(self.api_url, json=payload, headers=self.headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            manga = data.get('data', {}).get('manga', {})
            
            if not manga:
                return None
            
            title = self._get_title(manga.get('titles', []))
            cover_url = self._get_cover_url(manga.get('cover'))
            
            description = self._get_description(manga.get('localizations', []))
            
            genres = [tag.get('name', '') for tag in manga.get('tags', []) if tag.get('category') == 'GENRE']
            
            author = ''
            artist = ''
            for person in manga.get('persons', []):
                # В вашем JSON это поле mainStaff, но в коде выше persons. 
                # Если используете mainStaff из примера, логику нужно подправить.
                pass 

            # Для совместимости с вашим JSON (mainStaff):
            for staff in manga.get('mainStaff', []):
                if 'STORY' in staff.get('roles', []) or 'STORY_AND_ART' in staff.get('roles', []):
                    author = staff.get('person', {}).get('name', '')
                if 'ART' in staff.get('roles', []) or 'STORY_AND_ART' in staff.get('roles', []):
                    artist = staff.get('person', {}).get('name', '')

            branches = manga.get('branches', [])
            total_chapters = branches[0].get('chapters', 0) if branches else 0
            
            return {
                'title': title,
                'slug': slug,
                'description': description, # <--- Исправлено
                'cover_url': cover_url,
                'original_url': f'https://senkuro.me/manga/{slug}',
                'author': author,
                'artist': artist,
                'year': manga.get('releaseYear'),
                'genres': genres,
                'total_chapters': total_chapters,
            }
            
        except Exception as e:
            print(f"Error fetching manga details from Senkuro: {e}")
            return None

    def get_chapters(self, slug: str) -> list:
        manga_data = self.get_manga_details(slug)
        payload_manga = {
            "operationName": "fetchManga",
            "variables": {"slug": slug},
            "extensions": {"persistedQuery": {"version": 1, "sha256Hash": "6d8b28abb9a9ee3199f6553d8f0a61c005da8f5c56a88ebcf3778eff28d45bd5"}}
        }
        res = self._post_request(payload_manga)
        branches = res.get('data', {}).get('manga', {}).get('branches', [])
        if not branches: return []
        branch_id = branches[0]['id']

        all_chapters = []
        after = None
        while True:
            payload = {
                "operationName": "fetchMangaChapters",
                "variables": {"after": after, "branchId": branch_id, "orderBy": {"direction": "ASC", "field": "NUMBER"}},
                "extensions": {"persistedQuery": {"version": 1, "sha256Hash": "8c854e121f05aa93b0c37889e732410df9ea207b4186c965c845a8d970bdcc12"}}
            }
            data = self._post_request(payload)
            ch_data = data.get('data', {}).get('mangaChapters', {})
            for edge in ch_data.get('edges', []):
                node = edge.get('node', {})
                all_chapters.append({
                    'number': node.get('number', 0),
                    'volume': node.get('volume', 1),
                    'title': node.get('title', ''),
                    'url': node.get('slug', ''), 
                })
            if not ch_data.get('pageInfo', {}).get('hasNextPage'): break
            after = ch_data['pageInfo']['endCursor']
        return all_chapters

    def get_pages(self, **kwargs) -> list:
        """
        Теперь принимает slug напрямую из БД.
        Вызывается как: get_pages(chapter_slug='...')
        """
        chapter_slug = kwargs.get('chapter_slug')
        if not chapter_slug: return []

        payload = {
            "operationName": "fetchMangaChapter",
            "variables": {"cdnQuality": "auto", "slug": chapter_slug},
            "extensions": {"persistedQuery": {"version": 1, "sha256Hash": "8e166106650d3659d21e7aadc15e7e59e5def36f1793a9b15287c73a1e27aa50"}}
        }
        try:
            data = self._post_request(payload)
            pages = data.get('data', {}).get('mangaChapter', {}).get('pages', [])
            return [p['image']['original']['url'] for p in pages if p.get('image')]
        except Exception: return []
    def _get_description(self, localizations: list) -> str:
        """Извлекает и склеивает текст описания из вложенной структуры Tiptap"""
        # Ищем русскую локализацию, если нет — берем первую доступную
        target_loc = next((loc for loc in localizations if loc.get('lang') == 'RU'), None)
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
                paragraph_text = "".join([item.get('text', '') for item in content if item.get('type') == 'text'])
                full_text.append(paragraph_text)
        
        return "\n".join(full_text).strip()
    def _get_title(self, titles):
        return next((t['content'] for t in titles if t['lang'] == 'RU'), titles[0]['content'] if titles else '')
    
    def _get_cover_url(self, cover):
        if not cover: return ''
        return cover.get('original', {}).get('url') or cover.get('medium', {}).get('url', '')

    def _get_author(self, node):
        return next((p['name'] for p in node.get('persons', []) if p['role'] == 'AUTHOR'), '')