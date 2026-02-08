#base.py
from abc import ABC, abstractmethod

class BaseParser(ABC):
    """Базовый класс для всех парсеров"""
    
    @abstractmethod
    def search(self, query: str, limit: int = 20) -> list:
        """Поиск манги по запросу"""
        pass
    
    @abstractmethod
    def get_manga_details(self, slug: str) -> dict:
        """Получить детали манги"""
        pass
    
    @abstractmethod
    def get_chapters(self, slug: str) -> list:
        """Получить список глав"""
        pass
    @abstractmethod
    def get_pages(self, **kwargs) -> list:
        """Получить список страниц. Принимает аргументы через kwargs для гибкости."""
        pass