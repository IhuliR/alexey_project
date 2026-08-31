# Архитектура Formaslov

## Назначение системы

Formaslov — MVP для ручной разметки текстов. Авторизованный пользователь управляет своими документами и метками, выделяет фрагменты текста, сохраняет аннотации с абсолютными offsets и экспортирует разметку в JSON.

## Компоненты

```text
Browser
  └─ React SPA
       └─ REST /api/v1/
            └─ FastAPI
                 └─ PostgreSQL
```

FastAPI работает с PostgreSQL асинхронно через SQLAlchemy 2 и `asyncpg`. Django backend сохранён в `backend/` как legacy-реализация и источник существующих migrations. Текущий production compose пока продолжает запускать legacy Django; переключение deployment выполняется отдельно.

## Backend modules

- `app/api` — FastAPI routers, auth dependencies и формат ошибок;
- `app/models` — SQLAlchemy-модели существующих предметных таблиц;
- `app/schemas` — Pydantic-схемы API;
- `app/services` — небольшие функции обработки документов;
- `backend/` — legacy Django models, migrations и тесты.

Настройки FastAPI читаются из environment и `.env` через `pydantic-settings`. `SECRET_KEY`, CORS и параметры PostgreSQL сохраняют существующие имена переменных. SQLite fallback отсутствует.

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

FastAPI routers публикуют CRUD для:

- `/api/v1/documents/`;
- `/api/v1/labels/`;
- `/api/v1/annotations/`.

Нестандартные actions документов:

- `POST /api/v1/documents/upload/` — импорт UTF-8 `.txt`;
- `GET /api/v1/documents/{id}/chunks/` — абзацы и offsets для текущей страницы.

FastAPI реализует регистрацию, текущего пользователя, смену пароля и совместимые JWT endpoints. Подробный контракт находится в [API guide](API_GUIDE.md); OpenAPI schema и ReDoc генерируются автоматически.

### Documents

Document router фильтрует документы по текущему пользователю и назначает владельца на backend. Create/update принимают `multipart/form-data`. Переносы `CRLF`/`CR` нормализуются в `LF`.

`chunks` делит текст по пустым строкам и возвращает абсолютные `chunk_start`/`chunk_end`. Frontend запрашивает один chunk на страницу, поэтому offsets однозначно относятся к единственному элементу массива `chunk`.

### Labels

Label router фильтрует запросы по владельцу. Перед удалением используемой метки проверяются связанные аннотации и возвращается `409 Conflict` с кодом `label_in_use`.

### Annotations

Annotation router показывает только аннотации документов текущего пользователя и поддерживает фильтр `?document=<id>`. Валидация проверяет ownership документа и метки, offsets и вычисляет `text` по содержимому документа.

## Authentication и authorization

FastAPI dependency проверяет JWT access token и загружает активного пользователя. Клиент передаёт access token как `Authorization: Bearer <token>`.

Явные ownership-проверки поддерживают оба варианта:

- `user_id` для документов и меток;
- владельца документа для аннотаций.

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

В репозитории есть FastAPI image для локальной миграционной среды и три legacy production image:

- backend: Python 3.12, зависимости, Gunicorn;
- frontend: Node 20, `npm ci`, production build;
- gateway: Nginx с template конфигурации.

`infra/docker-compose.yml` рассчитан на deployment: использует опубликованные images, именованные volumes и внешнюю сеть `web`; локальные host ports не публикуются.

Существующий GitHub Actions workflow при push в `master` пока проверяет и разворачивает legacy Django backend. Переключение production CI/CD на FastAPI не входит в текущий этап.

Legacy workflow:

1. запускает flake8 и Django tests с PostgreSQL 16;
2. запускает frontend tests;
3. собирает и публикует backend, frontend и gateway images;
4. копирует compose-файл на host по SSH;
5. обновляет containers, выполняет migrations и `collectstatic`;
6. отправляет служебное уведомление после deploy job.

Настройка внешнего reverse proxy и TLS в репозитории отсутствует.

## Технические ограничения

- редактирование `TextDocument.content` не пересчитывает существующие offsets и `Annotation.text`;
- `Annotation.text` ограничен 500 символами, а API заранее не проверяет длину вычисленного фрагмента;
- пересекающиеся аннотации разрешены backend, но frontend при отрисовке принимает только непересекающиеся segments;
- `chunks` основан на разделении пустыми строками, а не на фиксированном размере;
- при `page_size > 1` API возвращает несколько chunks, но `chunk_start`, `chunk_end` и `chunk_index` становятся `null`;
- FastAPI OpenAPI schema генерируется автоматически; статическая schema остаётся только в legacy backend;
- production compose зависит от заранее созданной внешней Docker-сети `web` и внешнего reverse proxy.
