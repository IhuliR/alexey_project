# Formaslov

Formaslov is a web application for working with qualitative research texts in Russian. It lets a user upload materials, organize text documents, mark text fragments with labels, and export annotation results.

The project started as a Django / Django REST Framework application. The main backend API has been migrated to FastAPI and is used in production.

## Status

Formaslov is an MVP with a deployed FastAPI backend, React frontend, PostgreSQL persistence, Redis caching, and Celery background tasks through RabbitMQ. The project is still evolving, but the main document, annotation, import, and export flows are implemented.

## Key Features

- JWT authentication and user-owned data.
- Text document creation, editing, listing, and deletion.
- Single `.txt` upload and manual document creation.
- Batch ZIP import for research materials.
- `.txt` and `.docx` processing inside ZIP imports.
- Manual annotation of text fragments with absolute offsets.
- User-defined labels and categories with colors.
- Redis caching for frequently read label lists.
- Background import processing with status tracking.
- Background JSON export with status tracking and file download.
- FastAPI OpenAPI documentation.

## Tech Stack

**Backend**

- Python 3.12
- FastAPI
- SQLAlchemy 2
- Pydantic
- JWT authentication

**Database**

- PostgreSQL
- Alembic

**Background Tasks and Cache**

- Celery
- RabbitMQ
- Redis

**Frontend**

- React
- React Router
- Axios

**Infrastructure**

- Docker
- Docker Compose
- Nginx
- GitHub Actions
- Docker Hub

The repository still contains the previous Django / DRF backend for migration compatibility, regression tests, and rollback.

## Architecture

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

FastAPI handles the REST API, authentication, validation, database access, and task creation. PostgreSQL is the source of truth. Redis is used only as a cache layer. RabbitMQ is the Celery broker. The FastAPI service and Celery worker share local storage for uploaded import archives and generated export files.

More details are in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Background Processing

Batch imports and exports run outside the HTTP request lifecycle.

For batch import, the user uploads a ZIP archive. The API creates an import record, sends a Celery task through RabbitMQ, and returns `202 Accepted`. The worker reads `.txt` and `.docx` files, creates documents, stores per-file errors, and updates the import status in PostgreSQL. A damaged file does not have to fail the whole batch.

For export, the API creates an export job and returns `202 Accepted`. The worker reads the document, labels, and annotations from PostgreSQL, writes a JSON file, updates the export status, and the user downloads the completed file through a separate endpoint.

## API

The REST API uses the `/api/v1/` prefix.

Main endpoint groups:

- auth and user account endpoints;
- documents;
- imports;
- exports;
- labels;
- annotations.

FastAPI serves the generated API docs at:

- `/docs`
- `/redoc`
- `/openapi.json`

The full API contract and examples are in [docs/API_GUIDE.md](docs/API_GUIDE.md).

## Local Development

Create a local environment file:

```bash
cp .env.example .env
```

For local development, the root `docker-compose.yml` starts the FastAPI runtime and supporting services:

```bash
docker compose build api celery-worker
docker compose up -d db redis rabbitmq
docker compose run --rm api alembic upgrade head
docker compose up api celery-worker
```

The API is available at `http://127.0.0.1:8000/api/v1/`.

Useful service URLs:

```text
http://127.0.0.1:8000/health
http://127.0.0.1:8000/docs
http://127.0.0.1:8000/redoc
```

To run the frontend:

```bash
cd frontend
npm ci --legacy-peer-deps
npm start
```

Set `REACT_APP_API_URL` in `frontend/.env` when the API is not available at the default path:

```env
REACT_APP_API_URL=http://127.0.0.1:8000/api/v1/
```

The React app runs at `http://localhost:3000`.

## Tests

FastAPI tests:

```bash
python -m pytest tests -q
```

Frontend tests:

```bash
cd frontend
npm test -- --watchAll=false
```

Legacy Django regression tests:

```bash
cd backend
python manage.py test
```

CI runs backend tests, legacy Django tests, and frontend tests before building deployment images.

## Deployment

Production deployment uses Docker images built by GitHub Actions:

- FastAPI backend image;
- React frontend image;
- Nginx gateway image.

Production Compose runs:

- PostgreSQL;
- Redis;
- RabbitMQ;
- FastAPI backend;
- Celery worker;
- frontend static build;
- Nginx gateway.

The workflow runs tests, builds Docker images, pushes them to Docker Hub with commit SHA tags, applies Alembic migrations, starts the runtime services, and checks `/health`.

Deployment details, required environment variables, and rollback notes are in [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

## Project Structure

```text
app/                 FastAPI backend
alembic/             database migrations
tests/               FastAPI tests
frontend/            React frontend and frontend tests
infra/               production Docker Compose
nginx/               gateway image and Nginx template
backend/             legacy Django backend, migrations, and tests
docs/                project documentation
demo/                static demo artifact
```

## Legacy Django Backend

Formaslov was originally built with Django and Django REST Framework. The main API has since been migrated to FastAPI. The legacy Django backend remains in the repository for migration compatibility, regression tests, and rollback, but it is not the current production runtime.

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [API Guide](docs/API_GUIDE.md)
- [Deployment](docs/DEPLOYMENT.md)
- [FastAPI refactor brief](docs/FASTAPI_REFACTOR_BRIEF.md)

## License

[MIT](LICENSE)
