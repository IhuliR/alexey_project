# Formaslov

Formaslov — full-stack MVP для ручной разметки текстов. Пользователь создаёт или загружает документ, выделяет фрагменты, назначает им собственные метки и экспортирует результат в JSON.

## Возможности

- регистрация, вход по JWT и смена пароля;
- создание документа вручную или из UTF-8 `.txt`;
- пакетная загрузка документов из ZIP-архива;
- просмотр текста по абзацам с абсолютными offsets;
- создание цветных пользовательских меток;
- создание аннотаций;
- редактирование документов, удаление меток и аннотаций;
- экспорт документа, меток и аннотаций в JSON в браузере;
- read-only демо без регистрации.

## Backend: ключевые решения

- REST API на FastAPI с JWT-аутентификацией;
- ownership документов, меток и аннотаций ограничено текущим пользователем;
- backend не доверяет тексту выделения от клиента: `text` вычисляется по `content[start:end]`;
- backend проверяет принадлежность документа и метки, диапазон offsets и непустое выделение;
- переносы строк нормализуются при сохранении, чтобы offsets оставались согласованными;
- имена меток уникальны в рамках пользователя, а используемая метка защищена от удаления;
- список пользовательских меток кэшируется в Redis и инвалидируется при изменении меток;
- Celery worker через RabbitMQ обрабатывает пакетный импорт документов;
- PostgreSQL — единственный настроенный database backend;
- backend API покрыт тестами ownership, валидации, auth и нестандартных ответов.

## Стек

**Backend:** Python 3.12, FastAPI, Pydantic 2, SQLAlchemy 2, asyncpg, Alembic, PostgreSQL, Celery. Django / DRF сохранены как legacy-реализация на время миграции.

**Frontend:** React 19, React Router, Axios, Create React App.

**Infrastructure:** Docker, Docker Compose, Nginx, GitHub Actions, Docker Hub, Alembic, Redis, RabbitMQ.

## Архитектура

```text
Browser → React SPA → /api/v1/ → FastAPI → PostgreSQL
                                      └→ Redis cache
                                      └→ RabbitMQ → Celery worker
```

React хранит JWT в `localStorage`, централизованно добавляет access token и один раз пытается обновить его после `401`. Загруженный `.txt` не сохраняется как media-файл: backend декодирует UTF-8 и записывает текст в PostgreSQL.

Подробнее: [архитектура](docs/ARCHITECTURE.md).

### Миграция backend на FastAPI

Проект постепенно переводится с Django / DRF на FastAPI в рамках подготовки к пакетной обработке исследовательских материалов, фоновым задачам и будущим I/O-bound интеграциям.

Основной пользовательский API перенесён на FastAPI с сохранением существующих URL и JSON-контрактов. Django / DRF backend пока остаётся в репозитории как legacy-реализация, а SQLAlchemy-модели совместимы с созданной Django схемой PostgreSQL.

Подробнее о мотивации и планируемой архитектуре: [развитие backend](docs/FASTAPI_REFACTOR_BRIEF.md).

## Структура репозитория

```text
backend/             legacy Django backend, migrations и тесты
app/                 основной FastAPI backend
alembic/             миграции SQLAlchemy / Alembic
frontend/            React SPA и frontend-тесты
infra/               production Docker Compose
nginx/               gateway image и Nginx template
.github/workflows/   CI/CD для ветки master
docs/                архитектура, API и правила проекта
demo/                отдельный статический demo-артефакт
```

## Локальный запуск

Для backend нужны Python 3.12, PostgreSQL и переменные из `.env`. Production compose не публикует локальные порты и подключается к внешней Docker-сети, поэтому для разработки сервисы запускаются отдельно.

### 1. PostgreSQL, Redis и RabbitMQ

Например, локальную базу можно поднять контейнером:

```bash
docker run --name formaslov-postgres \
  -e POSTGRES_DB=django \
  -e POSTGRES_USER=django_user \
  -e POSTGRES_PASSWORD=some_password \
  -p 5432:5432 -d postgres:16-alpine
```

Redis можно поднять отдельно:

```bash
docker run --name formaslov-redis -p 6379:6379 -d redis:7-alpine
```

RabbitMQ для Celery:

```bash
docker run --name formaslov-rabbitmq \
  -p 5672:5672 -p 15672:15672 \
  -d rabbitmq:3.13-management-alpine
```

### 2. FastAPI backend

```bash
cp .env.example .env
```

Для запуска вне Docker измените в `.env`:

```env
DB_HOST=127.0.0.1
REDIS_URL=redis://127.0.0.1:6379/0
CELERY_BROKER_URL=amqp://guest:guest@127.0.0.1:5672//
DEBUG=True
```

Затем:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

API будет доступен по адресу `http://127.0.0.1:8000/api/v1/`. Служебные endpoints и документация:

```text
http://127.0.0.1:8000/health
http://127.0.0.1:8000/docs
http://127.0.0.1:8000/redoc
```

Для работы с PostgreSQL используются переменные окружения из `.env`. Также поддерживается `DATABASE_URL`. Redis подключается через `REDIS_URL`; TTL кэша задаётся `CACHE_TTL_SECONDS`. Celery использует RabbitMQ broker из `CELERY_BROKER_URL`. ZIP-архивы batch import временно сохраняются в `IMPORT_STORAGE_DIR`; лимиты задаются через `MAX_ARCHIVE_SIZE`, `MAX_ARCHIVE_FILES`, `MAX_DOCUMENT_SIZE` и `ALLOWED_DOCUMENT_EXTENSIONS`.

Baseline migration Alembic создаёт предметные таблицы в пустой БД, а в существующей Django-схеме оставляет их без изменений. Проверить состояние:

```bash
alembic current
```

Для запуска FastAPI, PostgreSQL, Redis, RabbitMQ и Celery worker через Docker Compose:

```bash
docker compose build api celery-worker
docker compose up -d db redis rabbitmq
docker compose run --rm api alembic upgrade head
docker compose up api celery-worker
```

Техническая Celery-задача `app.tasks.health.healthcheck` нужна только для проверки инфраструктуры. Пользовательская задача `app.tasks.imports.process_import` обрабатывает ZIP-импорт в очереди `imports`.

### 3. Legacy Django backend

Django-код пока не удалён. Его тесты и migrations можно запускать отдельно:

```bash
cd backend
python manage.py test
```

### 4. Frontend

Создайте `frontend/.env`:

```env
REACT_APP_API_URL=http://127.0.0.1:8000/api/v1/
```

Запустите приложение:

```bash
cd frontend
npm ci --legacy-peer-deps
npm start
```

Интерфейс откроется на `http://localhost:3000`. Переменные `REACT_APP_*` читаются на этапе запуска/сборки frontend.

## API

API использует префикс `/api/v1/`. Основные группы: auth, documents, imports, labels и annotations. Документы и ZIP-импорт принимают `multipart/form-data`; для меток и аннотаций frontend использует JSON. Все пользовательские ресурсы доступны только владельцу.

Полный контракт и примеры: [API guide](docs/API_GUIDE.md). OpenAPI schema доступна на `/openapi.json`, Swagger UI — на `/docs`, ReDoc — на `/redoc`.

## Deployment

Существующий production workflow пока использует legacy Django image с Gunicorn. Его переключение на FastAPI не входит в этот этап. Локальная FastAPI-инфраструктура запускается корневым `docker-compose.yml`.

TLS и конфигурация внешнего reverse proxy находятся вне этого репозитория.

## Документация

- [Архитектура](docs/ARCHITECTURE.md)
- [API guide](docs/API_GUIDE.md)

## License

[MIT](LICENSE)
