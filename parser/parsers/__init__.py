"""
Парсеры для различных источников манги
"""

from .base import BaseParser
from .mangalib import MangaLibParser

# Регистрация всех доступных парсеров
PARSERS = {
    'mangalib': MangaLibParser,
    # Добавьте другие парсеры здесь
    # 'senkuro': SenkuroParser,
    # 'mangahub': MangaHubParser,
}

def get_parser(source_key: str) -> BaseParser:
    """
    Получить экземпляр парсера по ключу источника
    
    Args:
        source_key: Ключ источника ('mangalib', 'senkuro' и т.д.)
    
    Returns:
        Экземпляр парсера или None если не найден
    """
    parser_class = PARSERS.get(source_key)
    if parser_class:
        return parser_class()
    return None

__all__ = ['BaseParser', 'MangaLibParser', 'PARSERS', 'get_parser']