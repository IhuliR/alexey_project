# Formaslov

Formaslov — веб-приложение для работы с русскоязычными текстами качественных исследований. В нём можно загружать материалы, организовывать текстовые документы, размечать фрагменты метками и экспортировать результаты аннотирования.

Проект начинался как приложение на Django / Django REST Framework. Основной backend API перенесён на FastAPI и используется в production.

## Статус

Formaslov — MVP с развёрнутым FastAPI backend, React frontend, PostgreSQL в качестве основного хранилища, Redis-кэшированием и фоновыми задачами Celery через RabbitMQ. Проект продолжает развиваться, но основные сценарии работы с документами, аннотациями, импортом и экспортом уже реализованы.

## Возможности

- JWT-аутентификация и данные, привязанные к пользователю.
- Создание, редактирование, просмотр списка и удаление текстовых документов.
- Одиночная загрузка `.txt` и ручное создание документов.
- Пакетный ZIP-импорт исследовательских материалов.
- Обработка `.txt` и `.docx` внутри ZIP-архивов.
- Ручная разметка текстовых фрагментов с абсолютными позициями (offsets).
- Пользовательские метки и категории с цветами.
- Redis-кэширование часто запрашиваемых списков меток.
- Фоновая обработка импорта с отслеживанием статуса.
- Фоновый JSON-экспорт с отслеживанием статуса и скачиванием файла.
- OpenAPI-документация FastAPI.

## Стек

**Backend**

- Python 3.12
- FastAPI
- SQLAlchemy 2
- Pydantic
- JWT-аутентификация

**База данных**

- PostgreSQL
- Alembic

**Фоновые задачи и кэш**

- Celery
- RabbitMQ
- Redis

**Frontend**

- React
- React Router
- Axios

**Инфраструктура**

- Docker
- Docker Compose
- Nginx
- GitHub Actions
- Docker Hub

В репозитории остаётся прежний Django / DRF backend для совместимости миграции, регрессионных тестов и отката.

## Архитектура

```text
React frontend
      |
    Nginx
      |
   FastAPI ------ Redis cache
    |  |
    |  +------ RabbitMQ ------ Celery worker
    |                              |
PostgreSQL -----------------------+
                                   |
                    shared import/export storage
```

FastAPI отвечает за REST API, аутентификацию, валидацию, доступ к базе данных и создание фоновых задач. PostgreSQL — основное хранилище данных. Redis используется только как слой кэширования. RabbitMQ работает как брокер Celery. Сервис FastAPI и Celery worker используют общее локальное хранилище для загруженных архивов импорта и сформированных файлов экспорта.

Подробности описаны в [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Фоновая обработка

Пакетный импорт и экспорт выполняются вне жизненного цикла HTTP-запроса.

При пакетном импорте пользователь загружает ZIP-архив. API создаёт запись импорта, отправляет задачу Celery через RabbitMQ и возвращает `202 Accepted`. Celery worker читает `.txt` и `.docx` файлы, создаёт документы, сохраняет ошибки по отдельным файлам и обновляет статус импорта в PostgreSQL. Повреждённый файл не обязан приводить к падению всего пакетного импорта.

При экспорте API создаёт задачу экспорта и возвращает `202 Accepted`. Celery worker читает документ, метки и аннотации из PostgreSQL, записывает JSON-файл, обновляет статус экспорта, а пользователь скачивает готовый файл через отдельный endpoint.

## API

REST API использует префикс `/api/v1/`.

Основные группы endpoints:

- auth и user account endpoints;
- documents;
- imports;
- exports;
- labels;
- annotations.

FastAPI отдаёт сгенерированную документацию API по адресам:

- `/docs`
- `/redoc`
- `/openapi.json`

Полный контракт API и примеры находятся в [docs/API_GUIDE.md](docs/API_GUIDE.md).

## Локальная разработка

Создайте локальный файл окружения:

```bash
cp .env.example .env
```

Для локальной разработки корневой `docker-compose.yml` запускает сервис FastAPI и вспомогательные сервисы:

```bash
docker compose build api celery-worker
docker compose up -d db redis rabbitmq
docker compose run --rm api alembic upgrade head
docker compose up api celery-worker
```

API доступен по адресу `http://127.0.0.1:8000/api/v1/`.

Полезные адреса сервисов:

```text
http://127.0.0.1:8000/health
http://127.0.0.1:8000/docs
http://127.0.0.1:8000/redoc
```

Для запуска frontend:

```bash
cd frontend
npm ci --legacy-peer-deps
npm start
```

Укажите `REACT_APP_API_URL` в `frontend/.env`, если API недоступен по стандартному пути:

```env
REACT_APP_API_URL=http://127.0.0.1:8000/api/v1/
```

React-приложение запускается на `http://localhost:3000`.

## Тесты

Тесты FastAPI:

```bash
python -m pytest tests -q
```

Тесты frontend:

```bash
cd frontend
npm test -- --watchAll=false
```

Регрессионные тесты legacy Django:

```bash
cd backend
python manage.py test
```

CI запускает тесты backend, регрессионные тесты legacy Django и тесты frontend перед сборкой Docker-образов для развёртывания.

## Развёртывание

Production-развёртывание использует Docker-образы, собранные через GitHub Actions:

- образ FastAPI backend;
- образ React frontend;
- образ Nginx gateway.

Production Compose запускает:

- PostgreSQL;
- Redis;
- RabbitMQ;
- FastAPI backend;
- Celery worker;
- статическую сборку frontend;
- Nginx gateway.

Workflow запускает тесты, собирает Docker-образы, публикует их в Docker Hub с тегами по commit SHA, применяет Alembic migrations, запускает сервисы приложения и проверяет `/health`.

Детали развёртывания, обязательные переменные окружения и заметки по откату описаны в [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

## Структура проекта

```text
app/                 FastAPI backend
alembic/             миграции базы данных
tests/               тесты FastAPI
frontend/            React frontend и тесты frontend
infra/               production Docker Compose
nginx/               образ gateway и шаблон Nginx
backend/             legacy Django backend, migrations и тесты
docs/                документация проекта
demo/                статический demo-артефакт
```

## Legacy Django Backend

Formaslov изначально был построен на Django и Django REST Framework. Сейчас основной API перенесён на FastAPI. Legacy Django backend остаётся в репозитории для совместимости миграции, регрессионных тестов и отката, но не является текущим production runtime.

## Документация

- [Архитектура](docs/ARCHITECTURE.md)
- [API Guide](docs/API_GUIDE.md)
- [Deployment](docs/DEPLOYMENT.md)
- [FastAPI refactor brief](docs/FASTAPI_REFACTOR_BRIEF.md)

## Лицензия

[MIT](LICENSE)
