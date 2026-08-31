# Formaslov

Formaslov — full-stack MVP для ручной разметки текстов. Пользователь создаёт или загружает документ, выделяет фрагменты, назначает им собственные метки и экспортирует результат в JSON.

## Возможности

- регистрация, вход по JWT и смена пароля;
- создание документа вручную или из UTF-8 `.txt`;
- просмотр текста по абзацам с абсолютными offsets;
- создание цветных пользовательских меток;
- создание аннотаций;
- редактирование документов, удаление меток и аннотаций;
- экспорт документа, меток и аннотаций в JSON в браузере;
- read-only демо без регистрации.

## Backend: ключевые решения

- REST API на Django REST Framework, Djoser и Simple JWT;
- ownership документов, меток и аннотаций ограничено текущим пользователем;
- backend не доверяет тексту выделения от клиента: `text` вычисляется по `content[start:end]`;
- serializer проверяет принадлежность документа и метки, диапазон offsets и непустое выделение;
- переносы строк нормализуются при сохранении, чтобы offsets оставались согласованными;
- имена меток уникальны в рамках пользователя, а используемая метка защищена от удаления;
- PostgreSQL — единственный настроенный database backend;
- backend API покрыт тестами ownership, валидации, auth и нестандартных ответов.

## Стек

**Backend:** Python 3.12, Django 6, Django REST Framework, Djoser, Simple JWT, PostgreSQL, Gunicorn.

**Frontend:** React 19, React Router, Axios, Create React App.

**Infrastructure:** Docker, Docker Compose, Nginx, GitHub Actions, Docker Hub.

## Архитектура

```text
Browser → React SPA → /api/v1/ → Nginx → Gunicorn → Django/DRF → PostgreSQL
```

React хранит JWT в `localStorage`, централизованно добавляет access token и один раз пытается обновить его после `401`. Загруженный `.txt` не сохраняется как media-файл: backend декодирует UTF-8 и записывает текст в PostgreSQL.

Подробнее: [архитектура](docs/ARCHITECTURE.md).

## Структура репозитория

```text
backend/             Django project, приложения api/core/users, тесты
frontend/            React SPA и frontend-тесты
infra/               production Docker Compose
nginx/               gateway image и Nginx template
.github/workflows/   CI/CD для ветки master
docs/                архитектура, API и правила проекта
demo/                отдельный статический demo-артефакт
```

## Локальный запуск

Для backend нужны Python 3.12, PostgreSQL и переменные из `.env`. Production compose не публикует локальные порты и подключается к внешней Docker-сети, поэтому для разработки сервисы запускаются отдельно.

### 1. PostgreSQL

Например, локальную базу можно поднять контейнером:

```bash
docker run --name formaslov-postgres \
  -e POSTGRES_DB=django \
  -e POSTGRES_USER=django_user \
  -e POSTGRES_PASSWORD=some_password \
  -p 5432:5432 -d postgres:16-alpine
```

### 2. Backend

```bash
cp .env.example .env
```

Для запуска вне Docker измените в `.env`:

```env
DB_HOST=127.0.0.1
DEBUG=True
```

Затем:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

API будет доступен по адресу `http://127.0.0.1:8000/api/v1/`, ReDoc — `http://127.0.0.1:8000/redoc/`.

### 3. Frontend

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

API использует префикс `/api/v1/`. Основные группы: auth, documents, labels и annotations. Документы принимают `multipart/form-data`; для меток и аннотаций frontend использует JSON. Все пользовательские ресурсы доступны только владельцу.

Полный контракт и примеры: [API guide](docs/API_GUIDE.md). Интерактивное представление статической OpenAPI schema доступно на `/redoc/` при запущенном backend.

## Deployment

Workflow для push в `master` запускает backend и frontend tests, собирает три Docker image (backend, frontend, gateway), публикует их в Docker Hub и обновляет удалённый Docker Compose host по SSH. Compose запускает PostgreSQL, Gunicorn и внутренний Nginx gateway; frontend image копирует production build в общий static volume. Gateway подключён к внешней сети `web`, рассчитанной на внешний reverse proxy.

TLS и конфигурация внешнего reverse proxy находятся вне этого репозитория.

## Документация

- [Архитектура](docs/ARCHITECTURE.md)
- [API guide](docs/API_GUIDE.md)

## License

[MIT](LICENSE)
