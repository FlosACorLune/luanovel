#__init__.py

from .base import BaseParser
from .mangalib import MangaLibParser
from .senkuro import SenkuroParser

PARSERS = {
    'mangalib': MangaLibParser,
    'senkuro': SenkuroParser,
    # 'mangahub': MangaHubParser,
}

def get_parser(source_key: str) -> BaseParser:
    parser_class = PARSERS.get(source_key)
    if parser_class:
        return parser_class()
    return None

__all__ = ['BaseParser', 'MangaLibParser', 'PARSERS', 'get_parser']