from .mangalib import MangaLibParser

# Словарь всех парсеров
PARSERS = {
    'mangalib': MangaLibParser,
    # В будущем добавите другие:
    # 'senkuro': SenkuroParser,
    # 'mangahub': MangaHubParser,
}

def get_parser(source: str):
    """Получить парсер по имени источника"""
    parser_class = PARSERS.get(source.lower())
    if parser_class:
        return parser_class()
    return None