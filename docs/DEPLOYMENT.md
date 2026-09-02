# Production deployment

Production запускается из Docker images без git checkout на сервере. GitHub Actions доставляет `infra/docker-compose.yml` в `/opt/projects/formaslov/docker-compose.yml`, а существующий `.env` остаётся только на сервере.

## Сервисы и данные

- `db` использует существующий persistent volume `pg_data`;
- `redis` хранит только кэш;
- `rabbitmq` используется как Celery broker;
- `backend` запускает FastAPI через Uvicorn;
- `celery-worker` слушает очереди `imports` и `exports`;
- `backend` и `celery-worker` используют общий volume `app_data`;
- `frontend` заполняет volume `static`, а `gateway` проксирует API и раздаёт SPA.

External network по умолчанию называется `web`, alias gateway остаётся `formaslov_gateway`.

## Environment

Перед первым FastAPI rollout в `/opt/projects/formaslov/.env` должны быть добавлены:

```env
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=amqp://guest:guest@rabbitmq:5672//
```

Существующие `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `SECRET_KEY`, `NGINX_SERVER_NAME` и `DOCKER_USERNAME` сохраняются. Пути import/export задаются production Compose внутри общего `/app_data`; менять их в server `.env` не требуется.

`IMAGE_TAG` передаётся deployment workflow и равен commit SHA. Для ручного запуска можно использовать `IMAGE_TAG=latest`. Имя external network меняется только при необходимости через `WEB_NETWORK_NAME`.

## Первый rollout

1. Убедиться, что PostgreSQL backup проверен через `pg_restore` и external network `web` существует.
2. Добавить новые environment variables в server `.env`.
3. Настроить required reviewer для GitHub environment `production` и подтвердить deployment после успешных tests/build.
4. Workflow сохранит legacy compose и локальные pre-FastAPI image tags, поднимет infrastructure, выполнит `alembic upgrade head`, затем переключит backend и gateway.
5. Проверить `/health`, вход, документы, batch import и background export.

Workflow не выполняет `docker compose down`, не удаляет volumes и не запускает Alembic downgrade. Повторный запуск с тем же SHA безопасен.

## Проверка

На сервере:

```bash
cd /opt/projects/formaslov
sudo docker compose ps
sudo docker compose exec -T backend \
  python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/health').read().decode())"
sudo docker compose exec -T gateway wget -qO- http://127.0.0.1/health
```

Публично проверить `https://<NGINX_SERVER_NAME>/health`, `/docs` и основной API.

## Rollback

Для первого FastAPI rollout workflow сохраняет `docker-compose.legacy.yml` и локальные images `formaslov_backend:pre-fastapi`, `formaslov_frontend:pre-fastapi`, `formaslov_gateway:pre-fastapi`.

```bash
cd /opt/projects/formaslov
sudo docker compose stop gateway backend celery-worker redis rabbitmq
sudo docker compose -f docker-compose.legacy.yml up -d db backend frontend gateway
```

Для следующих deployments предыдущий commit SHA хранится в
`.previous-image-tag`, а предыдущая конфигурация — в
`docker-compose.previous.yml`:

```bash
cd /opt/projects/formaslov
cp docker-compose.previous.yml docker-compose.yml
IMAGE_TAG=$(cat .previous-image-tag) \
  sudo --preserve-env=IMAGE_TAG docker compose up -d backend celery-worker frontend gateway
```

Rollback не удаляет `pg_data`, `app_data` или другие volumes и не выполняет downgrade migrations. Таблицы `ImportBatch` и `ExportJob` обратно совместимы с legacy runtime и могут оставаться в PostgreSQL.

После переключения production runtime Django source, migrations и tests остаются в репозитории. Django admin в FastAPI deployment недоступен; при необходимости он возвращается вместе с legacy compose и pre-FastAPI images.
