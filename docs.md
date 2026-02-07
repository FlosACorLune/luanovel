# luanovel - educational python/django final project

## dependency
[[requirements.txt]]

## apps
Manga - Модели (Manga, Chapter, Genre, Author и т.д.) Отображение контента (список манги, читалка) API для фронтенда

Parser - Парсеры для разных сайтов Management команды для запуска парсинга Proxy функционал Обновление данных

Users - Регистрация/авторизация Профили? Закладки, история чтения Комментарии

## Models
### Manga

### User

### Parser

## API IDEA
127.0.0.1:8000 - main page
127.0.0.1:8000/manga/MANGAID--star-fostered-swordmaster - 
127.0.0.1:8000/manga/star-fostered-swordmaster - about title? just show Title name and Description 
127.0.0.1:8000/manga/star-fostered-swordmaster/chapters - list of chapters
127.0.0.1:8000/manga/star-fostered-swordmaster/chapters/215670481645225498/pages/1 - place where users read manga

127.0.0.1:8000/users/@190296960576538142 - user ID 
127.0.0.1:8000/users/@190296960576538142/bookmarks - bookmarks


API example 
https://api.cdnlibs.org/api/

https://api.cdnlibs.org/api/manga/167978--isekai-de-haishin-katsudou-wo-shitara-tairyou-no-yandere-shinja-wo-umidashite-shimatta-ken/relations

https://api.cdnlibs.org/api/manga/167978--isekai-de-haishin-katsudou-wo-shitara-tairyou-no-yandere-shinja-wo-umidashite-shimatta-ken
?fields[]=background&fields[]=eng_name&fields[]=otherNames&fields[]=summary&fields[]=releaseDate&fields[]=type_id&fields[]=caution&fields[]=views&fields[]=close_view&fields[]=rate_avg&fields[]=rate&fields[]=genres&fields[]=tags&fields[]=teams&fields[]=user&fields[]=franchise&fields[]=authors&fields[]=publisher&fields[]=userRating&fields[]=moderated&fields[]=metadata&fields[]=metadata.count&fields[]=metadata.close_comments&fields[]=manga_status_id&fields[]=chap_count&fields[]=status_id&fields[]=artists&fields[]=format


Приложение manga: Модели и админка.
Приложение parser: Скрипты, которые наполняют базу.
Приложение api: Отдает данные в JSON (как api.cdnlibs.org).
Приложение users: Отдает данные в JSON (как api.cdnlibs.org). но поскольку для не имеет смысла у меня будет выглядит 
127.0.0.1:8000/api/


## ENDPOINT часть API
get - /categories/
get - /manga/ - http code reponse(200/404/500) + json response