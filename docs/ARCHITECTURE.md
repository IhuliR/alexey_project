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
                 └─ Redis cache
                 └─ RabbitMQ ─ Celery worker
```

FastAPI работает с PostgreSQL асинхронно через SQLAlchemy 2 и `asyncpg`. Redis используется как cache layer для списка пользовательских меток; PostgreSQL остаётся source of truth. RabbitMQ используется как broker Celery, а отдельный worker выполняет фоновые задачи. Django backend сохранён в `backend/` как legacy-реализация и источник существующих migrations. Текущий production compose пока продолжает запускать legacy Django; переключение deployment выполняется отдельно.

## Backend modules

- `app/api` — FastAPI routers, auth dependencies и формат ошибок;
- `app/core/cache.py` — простой Redis JSON-cache helper;
- `app/models` — SQLAlchemy-модели существующих предметных таблиц;
- `app/schemas` — Pydantic-схемы API;
- `app/services` — небольшие функции обработки документов и cache-сценариев;
- `app/tasks` — Celery application и фоновые задачи;
- `backend/` — legacy Django models, migrations и тесты.

Настройки FastAPI читаются из environment и `.env` через `pydantic-settings`. `SECRET_KEY`, CORS, параметры PostgreSQL, `REDIS_URL` и `CELERY_BROKER_URL` сохраняют плоскую env-конфигурацию. SQLite fallback отсутствует.

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
- `/api/v1/imports/`;
- `/api/v1/exports/`;
- `/api/v1/labels/`;
- `/api/v1/annotations/`.

Нестандартные actions документов:

- `POST /api/v1/documents/upload/` — импорт UTF-8 `.txt`;
- `GET /api/v1/documents/{id}/chunks/` — абзацы и offsets для текущей страницы.

Batch import:

- `POST /api/v1/imports/` — загрузка ZIP-архива и постановка фоновой задачи;
- `GET /api/v1/imports/{id}/` — статус batch import;
- `GET /api/v1/imports/{id}/items/` — результаты отдельных файлов.

Background export:

- `POST /api/v1/exports/` — постановка JSON-экспорта документа;
- `GET /api/v1/exports/{id}/` — статус export job;
- `GET /api/v1/exports/{id}/download/` — скачивание готового файла.

FastAPI реализует регистрацию, текущего пользователя, смену пароля и совместимые JWT endpoints. Подробный контракт находится в [API guide](API_GUIDE.md); OpenAPI schema и ReDoc генерируются автоматически.

### Documents

Document router фильтрует документы по текущему пользователю и назначает владельца на backend. Create/update принимают `multipart/form-data`. Переносы `CRLF`/`CR` нормализуются в `LF`.

`chunks` делит текст по пустым строкам и возвращает абсолютные `chunk_start`/`chunk_end`. Frontend запрашивает один chunk на страницу, поэтому offsets однозначно относятся к единственному элементу массива `chunk`.

### Labels

Label router фильтрует запросы по владельцу. Перед удалением используемой метки проверяются связанные аннотации и возвращается `409 Conflict` с кодом `label_in_use`.

`GET /api/v1/labels/` читает список меток из Redis по ключу текущего пользователя. При cache miss данные загружаются из PostgreSQL и сохраняются с TTL. Создание, изменение и удаление меток удаляют cache key этого пользователя. Если Redis временно недоступен, API логирует warning и продолжает читать данные из PostgreSQL.

### Annotations

Annotation router показывает только аннотации документов текущего пользователя и поддерживает фильтр `?document=<id>`. Валидация проверяет ownership документа и метки, offsets и вычисляет `text` по содержимому документа.

### Imports

Import router принимает ZIP-архив через `multipart/form-data`, сохраняет его во временную директорию из `IMPORT_STORAGE_DIR`, создаёт `ImportBatch` и отправляет Celery-задачу `app.tasks.imports.process_import` в очередь `imports`. HTTP-request возвращает `202 Accepted` и не ждёт обработки файлов.

Worker последовательно обрабатывает файлы архива, поддерживает `.txt` и `.docx`, использует общую логику создания `TextDocument`, обновляет счётчики batch и пишет ошибку в `ImportItem`, если конкретный файл не может быть импортирован. Batch принадлежит текущему пользователю; статус и элементы чужого импорта скрываются через `404`.

### Exports

Export router принимает JSON-запрос с `document_id` и `format`, проверяет ownership документа, создаёт `ExportJob` и отправляет Celery-задачу `app.tasks.exports.generate_export` в очередь `exports`. HTTP-request возвращает `202 Accepted` и не ждёт формирования файла.

Worker перечитывает документ, метки пользователя и аннотации документа из PostgreSQL, формирует JSON schema v2, совместимую с текущим frontend export, сохраняет файл в директорию из `EXPORT_STORAGE_DIR` и переводит job в `completed`. Статус и download доступны только владельцу export job; до завершения download возвращает `409 Conflict`.

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

Рабочая страница документа загружает документ, метки, аннотации и chunk. Browser selection преобразуется из локальных координат chunk в абсолютные offsets. Существующий frontend по-прежнему умеет формировать JSON-export локально; backend дополнительно предоставляет фоновый export API для последующей интеграции UI.

Публичный `/demo` использует статические frontend-данные и не обращается к API. Management command `seed_demo_data` — отдельная локальная/admin-утилита.

## Хранение данных

Основное хранилище — PostgreSQL. Redis хранит только временный JSON-кэш списка меток и не является source of truth. Загружаемый `.txt` декодируется как UTF-8 и сохраняется в `TextDocument.content`; исходный файл в media storage не записывается. ZIP-архивы batch import временно хранятся на диске до завершения worker-задачи. Готовые JSON export-файлы хранятся локально в отдельной директории. Docker volumes используются для PostgreSQL, общей директории import archives, export files, Django static и media directory.

## Фоновые задачи

Celery настроен с RabbitMQ broker и одним worker-контейнером. Пользовательская задача `app.tasks.imports.process_import` выполняет пакетный импорт документов из ZIP-архива в очереди `imports`. Пользовательская задача `app.tasks.exports.generate_export` формирует JSON-файл экспорта документа в очереди `exports`.

Result backend не настроен: текущим фоновым операциям достаточно доставки и выполнения задачи. Пользовательское состояние хранится в PostgreSQL-моделях `ImportBatch` и `ExportJob`.

## Infrastructure и deployment

В репозитории есть FastAPI image для локальной среды и три legacy production image:

- backend: Python 3.12, зависимости, Gunicorn;
- frontend: Node 20, `npm ci`, production build;
- gateway: Nginx с template конфигурации.

`infra/docker-compose.yml` рассчитан на deployment: использует опубликованные images, именованные volumes и внешнюю сеть `web`; локальные host ports не публикуются.

Корневой `docker-compose.yml` используется для локальной FastAPI-инфраструктуры и поднимает `api`, `db`, `redis`, `rabbitmq` и `celery-worker`.

Существующий GitHub Actions workflow при push в `master` пока проверяет и разворачивает legacy Django backend. Переключение production CI/CD на FastAPI требует отдельной deployment-работы.

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
- автоматическая retention/cleanup готовых export-файлов пока отсутствует;
- Celery result backend не настроен;
- production compose зависит от заранее созданной внешней Docker-сети `web` и внешнего reverse proxy.
