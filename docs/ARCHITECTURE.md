# Архитектура Formaslov

## Назначение системы

Formaslov — MVP для ручной разметки текстов. Авторизованный пользователь управляет своими документами и метками, выделяет фрагменты текста, сохраняет аннотации с абсолютными offsets и экспортирует разметку в JSON.

## Компоненты

```text
Browser
  └─ React SPA
       └─ REST /api/v1/
            └─ Django REST Framework
                 └─ PostgreSQL
```

В production-структуре запросы принимает Nginx gateway. Он отдаёт собранный React frontend, проксирует `/api/` и `/redoc/` в Gunicorn/Django и подключается к внешней Docker-сети для upstream reverse proxy.

## Backend applications

- `config` — Django settings, корневой URL routing и WSGI/ASGI entrypoints;
- `users` — кастомная модель `MyUser` на базе `AbstractUser`;
- `core` — модели документов, меток и аннотаций, migrations и demo seed command;
- `api` — serializers, viewsets, permissions, router и API tests.

Локально `python-dotenv` загружает `.env` из корня репозитория; в containers значения передаются окружением. `SECRET_KEY` обязателен; `DEBUG`, hosts, CORS/CSRF, параметры PostgreSQL, static/media paths и security flags задаются environment. SQLite fallback отсутствует.

## Модели и связи

```text
MyUser 1 ─── * TextDocument 1 ─── * Annotation * ─── 1 Label * ─── 1 MyUser
```

### `TextDocument`

- `user` — владелец;
- `title` — название, fallback `Новый документ`;
- `slug` — генерируется из title и уникален в рамках пользователя;
- `original_filename` — исходное имя загруженного файла;
- `content` — полный текст;
- `created_at` — время создания.

При изменении title slug генерируется заново. Одинаковые slug у разных пользователей допустимы.

### `Label`

- принадлежит пользователю;
- содержит `name` и строковое поле `color`, используемое frontend как HEX-цвет;
- имя уникально в рамках пользователя;
- связь из `Annotation` использует `PROTECT`, поэтому задействованную метку нельзя удалить.

### `Annotation`

- связывает документ и метку;
- хранит полуоткрытый диапазон `[start, end)` в `document.content`;
- хранит вычисленный backend фрагмент `text`;
- удаляется вместе с документом, но защищает используемую метку от удаления.

## API layer

`DefaultRouter` публикует CRUD для:

- `/api/v1/documents/`;
- `/api/v1/labels/`;
- `/api/v1/annotations/`.

Нестандартные actions документов:

- `POST /api/v1/documents/upload/` — импорт UTF-8 `.txt`;
- `GET /api/v1/documents/{id}/chunks/` — абзацы и offsets для текущей страницы.

Djoser и Simple JWT добавляют регистрацию, текущего пользователя, смену пароля и операции с JWT. Подробный контракт находится в [API guide](API_GUIDE.md); статическая OpenAPI schema отдается через ReDoc на `/redoc/`.

### Documents

`TextDocumentViewSet.get_queryset()` фильтрует документы по `request.user`, а `perform_create()` назначает владельца. Из-за `MultiPartParser` create/update принимают `multipart/form-data`. Переносы `CRLF`/`CR` нормализуются в `LF`.

`chunks` делит текст по пустым строкам и возвращает абсолютные `chunk_start`/`chunk_end`. Frontend запрашивает один chunk на страницу, поэтому offsets однозначно относятся к единственному элементу массива `chunk`.

### Labels

`LabelViewSet` фильтрует queryset и назначает владельца на backend. При удалении используемой метки перехватывается `ProtectedError` и возвращается `409 Conflict` с кодом `label_in_use`.

### Annotations

`AnnotationViewSet` показывает только аннотации документов текущего пользователя и поддерживает фильтр `?document=<id>`. Serializer ограничивает selectable documents и labels владельцем, повторно проверяет ownership, проверяет offsets и вычисляет `text` по содержимому документа.

## Authentication и authorization

DRF по умолчанию использует `JWTAuthentication` и `IsAuthenticated`. Клиент передаёт access token как `Authorization: Bearer <token>`.

Object-level `IsAuthor` поддерживает оба варианта ownership:

- `obj.user` для документов и меток;
- `obj.document.user` для аннотаций.

Фильтрация queryset скрывает чужие объекты до object-level проверки: обращение к чужому ID обычно возвращает `404`, а не раскрывает существование объекта.

## Frontend/backend interaction

React routes:

- публичные: `/`, `/about`, `/technologies`, `/demo`, `/login`, `/register`;
- защищённые: `/documents`, `/documents/:id`, `/labels`, `/account`.

Общий Axios client читает `REACT_APP_API_URL`, добавляет access token и после первого `401` пытается получить новый access token через refresh endpoint. При неудаче токены удаляются.

Рабочая страница документа загружает документ, метки, аннотации и chunk. Browser selection преобразуется из локальных координат chunk в абсолютные offsets. Экспорт формируется полностью на frontend и не имеет отдельного backend endpoint.

Публичный `/demo` использует статические frontend-данные и не обращается к API. Management command `seed_demo_data` — отдельная локальная/admin-утилита.

## Хранение данных

Основное хранилище — PostgreSQL. Загружаемый `.txt` декодируется как UTF-8 и сохраняется в `TextDocument.content`; исходный файл в media storage не записывается. Docker volumes используются для PostgreSQL, Django static и media directory.

## Infrastructure и deployment

В репозитории есть три image definition:

- backend: Python 3.12, зависимости, Gunicorn;
- frontend: Node 20, `npm ci`, production build;
- gateway: Nginx с template конфигурации.

`infra/docker-compose.yml` рассчитан на deployment: использует опубликованные images, именованные volumes и внешнюю сеть `web`; локальные host ports не публикуются.

GitHub Actions при push в `master`:

1. запускает flake8 и Django tests с PostgreSQL 16;
2. запускает frontend tests;
3. собирает и публикует backend, frontend и gateway images;
4. копирует compose-файл на host по SSH;
5. обновляет containers, выполняет migrations и `collectstatic`;
6. отправляет служебное уведомление после deploy job.

Настройка внешнего reverse proxy и TLS в репозитории отсутствует.

## Технические ограничения

- редактирование `TextDocument.content` не пересчитывает существующие offsets и `Annotation.text`;
- `Annotation.text` ограничен 500 символами, а serializer заранее не проверяет длину вычисленного фрагмента;
- пересекающиеся аннотации разрешены backend, но frontend при отрисовке принимает только непересекающиеся segments;
- `chunks` основан на разделении пустыми строками, а не на фиксированном размере;
- при `page_size > 1` API возвращает несколько chunks, но `chunk_start`, `chunk_end` и `chunk_index` становятся `null`;
- OpenAPI schema хранится статически и должна обновляться вручную вместе с API;
- production compose зависит от заранее созданной внешней Docker-сети `web` и внешнего reverse proxy.
