# API guide

## Общая информация

- Base URL: `/api/v1/`
- Основной формат: JSON
- Documents create/update и ZIP import: `multipart/form-data`
- Auth header: `Authorization: Bearer <access_token>`
- По умолчанию API требует аутентификацию; исключения — регистрация и JWT endpoints.

Все documents, imports, labels и annotations изолированы по текущему пользователю. Чужой detail resource обычно выглядит как отсутствующий и возвращает `404 Not Found`.

## Краткая карта endpoints

| Метод | Endpoint | Назначение |
|---|---|---|
| POST | `users/` | регистрация |
| GET | `users/me/` | текущий пользователь |
| POST | `users/set_password/` | смена пароля |
| POST | `jwt/create/` | access + refresh tokens |
| POST | `jwt/refresh/` | новый access token |
| POST | `jwt/verify/` | проверка token |
| GET, POST | `documents/` | список и создание |
| GET, PUT, PATCH, DELETE | `documents/{id}/` | документ |
| POST | `documents/upload/` | импорт UTF-8 `.txt` |
| GET | `documents/{id}/chunks/` | chunks и offsets |
| POST | `imports/` | запуск batch import из ZIP |
| GET | `imports/{id}/` | статус batch import |
| GET | `imports/{id}/items/` | результаты файлов batch import |
| POST | `exports/` | запуск фонового JSON export |
| GET | `exports/{id}/` | статус export job |
| GET | `exports/{id}/download/` | скачивание готового export |
| GET, POST | `labels/` | список и создание |
| GET, PUT, PATCH, DELETE | `labels/{id}/` | метка |
| GET, POST | `annotations/` | список и создание |
| GET, PUT, PATCH, DELETE | `annotations/{id}/` | аннотация |

URL в таблице указаны относительно `/api/v1/`. Router также поддерживает стандартный `OPTIONS`.

## Authentication

### Регистрация

```http
POST /api/v1/users/
Content-Type: application/json
```

```json
{
  "username": "anna",
  "password": "Strong-password-42"
}
```

Поле `email` также принимается, но не обязательно. Успех: `201 Created`:

```json
{
  "email": "",
  "username": "anna",
  "id": 7
}
```

Password проходит стандартные Django validators и никогда не возвращается в response.

### JWT

Получить пару tokens:

```http
POST /api/v1/jwt/create/
Content-Type: application/json
```

```json
{
  "username": "anna",
  "password": "Strong-password-42"
}
```

```json
{
  "refresh": "<refresh_token>",
  "access": "<access_token>"
}
```

Обновить access token:

```http
POST /api/v1/jwt/refresh/
Content-Type: application/json
```

```json
{"refresh": "<refresh_token>"}
```

Проверить token:

```http
POST /api/v1/jwt/verify/
Content-Type: application/json
```

```json
{"token": "<token>"}
```

Успешные JWT операции возвращают `200 OK`. Access token передаётся в защищённые endpoints:

```http
Authorization: Bearer <access_token>
```

### Текущий пользователь и пароль

```http
GET /api/v1/users/me/
Authorization: Bearer <access_token>
```

```json
{
  "id": 7,
  "username": "anna"
}
```

Смена пароля:

```http
POST /api/v1/users/set_password/
Authorization: Bearer <access_token>
Content-Type: application/json
```

```json
{
  "current_password": "Strong-password-42",
  "new_password": "Updated-password-84",
  "re_new_password": "Updated-password-84"
}
```

Успех: `204 No Content`. Djoser проверяет текущий пароль, совпадение новых паролей и Django password validators.

## Documents

Document representation:

```json
{
  "id": 12,
  "user": 7,
  "title": "Тёзка",
  "slug": "tezka",
  "original_filename": "Тёзка.txt",
  "content": "Полный текст",
  "created_at": "2026-01-01T10:00:00Z"
}
```

`user`, `slug` и `created_at` read-only. Title очищается от внешних пробелов. При пустом title используется stem `original_filename`, затем `Новый документ`. Slug генерируется и остаётся уникальным в рамках пользователя; при изменении title он пересоздаётся.

### Список

```http
GET /api/v1/documents/
Authorization: Bearer <access_token>
```

Без `limit` response — массив документов. При `?limit=<n>&offset=<n>` включается DRF LimitOffsetPagination:

```json
{
  "count": 2,
  "next": null,
  "previous": null,
  "results": []
}
```

### Создание и изменение

```http
POST /api/v1/documents/
Authorization: Bearer <access_token>
Content-Type: multipart/form-data
```

| Поле | Обязательное | Описание |
|---|---:|---|
| `content` | да | полный текст |
| `title` | нет | название |
| `original_filename` | нет | исходное имя файла |

```bash
curl -X POST http://127.0.0.1:8000/api/v1/documents/ \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -F "title=Пример" \
  -F $'content=Первый абзац\n\nВторой абзац'
```

Успех: `201 Created`. Backend нормализует `\r\n` и `\r` в `\n`.

`PUT /documents/{id}/` и `PATCH /documents/{id}/` также требуют `multipart/form-data`; успех — `200 OK`. Удаление: `DELETE /documents/{id}/` → `204 No Content`. Удаление документа каскадно удаляет его annotations.

> Изменение `content` не пересчитывает существующие annotation offsets и сохранённый `text`.

### Импорт файла

```http
POST /api/v1/documents/upload/
Authorization: Bearer <access_token>
Content-Type: multipart/form-data
```

Единственное поле — `file`. Backend принимает имя, оканчивающееся на `.txt` в нижнем регистре, и UTF-8 content. Файл декодируется и сразу сохраняется как document; сам файл в media storage не помещается.

```bash
curl -X POST http://127.0.0.1:8000/api/v1/documents/upload/ \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -F "file=@example.txt;type=text/plain"
```

Возможные `400`: поле отсутствует, расширение не `.txt`, содержимое не UTF-8.

### Chunks

```http
GET /api/v1/documents/12/chunks/?page=1&page_size=1
Authorization: Bearer <access_token>
```

Текст делится на непустые блоки, разделённые одной или несколькими пустыми строками. Response:

```json
{
  "document_id": 12,
  "page": 1,
  "page_size": 1,
  "has_next": true,
  "has_prev": false,
  "total_chunks": 2,
  "chunk": ["Первый абзац"],
  "chunk_index": 0,
  "chunk_start": 0,
  "chunk_end": 12
}
```

`chunk_start` и `chunk_end` — абсолютный полуоткрытый диапазон `[start, end)` в сохранённом `content`. При `page_size > 1` массив содержит несколько chunks, а `chunk_index`, `chunk_start` и `chunk_end` равны `null`.

Для пустого документа возвращается пустой `chunk`, `total_chunks: 0` и null offsets. Нечисловые или неположительные параметры дают `400`, страница за диапазоном — `404`.

## Imports

Batch import принимает ZIP-архив и создаёт документы текущего пользователя в фоновой Celery-задаче.

```http
POST /api/v1/imports/
Authorization: Bearer <access_token>
Content-Type: multipart/form-data
```

Единственное поле — `file`. API принимает только `.zip`, сохраняет архив во временную директорию, создаёт запись импорта, отправляет `app.tasks.imports.process_import` в очередь `imports` и сразу возвращает `202 Accepted`.

```json
{
  "id": 31,
  "status": "pending",
  "files_total": 0,
  "files_processed": 0,
  "files_failed": 0,
  "created_at": "2026-01-01T10:00:00Z",
  "started_at": null,
  "finished_at": null,
  "error": ""
}
```

Worker поддерживает `.txt` и `.docx`. Неподдерживаемые расширения, повреждённые документы и пустые документы фиксируются как ошибки отдельных файлов; batch завершается как `completed_with_errors`, если хотя бы один файл был обработан с ошибкой.

Статус:

```http
GET /api/v1/imports/31/
Authorization: Bearer <access_token>
```

Возможные статусы batch: `pending`, `processing`, `completed`, `completed_with_errors`, `failed`.

Элементы:

```http
GET /api/v1/imports/31/items/
Authorization: Bearer <access_token>
```

```json
[
  {
    "id": 101,
    "filename": "interview-1.txt",
    "status": "processed",
    "document_id": 44,
    "error": ""
  }
]
```

Возможные статусы файла: `pending`, `processed`, `failed`.

## Exports

Фоновый export формирует JSON-файл документа, меток пользователя и аннотаций документа вне HTTP-request.

```http
POST /api/v1/exports/
Authorization: Bearer <access_token>
Content-Type: application/json
```

```json
{
  "document_id": 12,
  "format": "json"
}
```

API проверяет ownership документа, создаёт `ExportJob`, отправляет `app.tasks.exports.generate_export` в очередь `exports` и сразу возвращает `202 Accepted`.

```json
{
  "id": 42,
  "user_id": 7,
  "document_id": 12,
  "format": "json",
  "status": "pending",
  "created_at": "2026-01-01T10:00:00Z",
  "started_at": null,
  "finished_at": null,
  "error": ""
}
```

Статус:

```http
GET /api/v1/exports/42/
Authorization: Bearer <access_token>
```

Возможные статусы: `pending`, `processing`, `completed`, `failed`.

Download:

```http
GET /api/v1/exports/42/download/
Authorization: Bearer <access_token>
```

Скачивание доступно только для `completed` job владельца. Pending, processing и failed jobs возвращают `409 Conflict`. Чужой export возвращает `404 Not Found`. Абсолютный server path в API не возвращается.

Файл отдаётся как `application/json` с именем вида:

```text
<document-slug>_export.json
```

JSON сохраняет текущую schema v2 frontend export:

```json
{
  "schema_version": 2,
  "exported_at": "2026-01-01T11:00:00Z",
  "document": {
    "id": 12,
    "title": "Тёзка",
    "slug": "tezka",
    "original_filename": "Тёзка.txt",
    "created_at": "2026-01-01T10:00:00Z",
    "content": "Полный текст"
  },
  "labels": [
    {
      "id": 4,
      "name": "Персонаж",
      "color": "#ffcc00"
    }
  ],
  "annotations": [
    {
      "id": 31,
      "start": 0,
      "end": 6,
      "text": "Полный",
      "label": {
        "id": 4,
        "name": "Персонаж",
        "color": "#ffcc00"
      },
      "label_id": 4,
      "created_at": "2026-01-01T10:05:00Z"
    }
  ]
}
```

## Labels

Label representation:

```json
{
  "id": 4,
  "name": "Персонаж",
  "color": "#ffcc00"
}
```

- `GET /labels/` → массив меток пользователя;
- `POST /labels/` → `201 Created`;
- `GET /labels/{id}/` → одна метка;
- `PUT|PATCH /labels/{id}/` → обновление;
- `DELETE /labels/{id}/` → `204 No Content`.

Список меток кэшируется в Redis отдельно для каждого пользователя. Это не меняет формат ответа API; при изменении меток соответствующий кэш пользователя удаляется.

Create example:

```json
{
  "name": "Персонаж",
  "color": "#ffcc00"
}
```

`name` обязательно, не длиннее 100 символов и уникально в рамках пользователя. `color` — строка до 7 символов с default `#ffff00`; API отдельно не проверяет HEX-формат.

Если label используется annotations, delete возвращает `409 Conflict`:

```json
{
  "detail": "Нельзя удалить метку «Персонаж»: она используется в 2 аннотациях. Сначала удалите или измените эти аннотации.",
  "code": "label_in_use",
  "annotations_count": 2
}
```

## Annotations

Annotation representation:

```json
{
  "id": 31,
  "document": 12,
  "label": 4,
  "start": 0,
  "end": 6,
  "text": "Начало",
  "created_at": "2026-01-01T10:05:00Z"
}
```

- `GET /annotations/` → массив annotations пользователя;
- `GET /annotations/?document=12` → фильтр по document ID;
- `POST /annotations/` → `201 Created`;
- `GET /annotations/{id}/` → одна annotation;
- `PUT|PATCH /annotations/{id}/` → обновление и повторное вычисление `text`;
- `DELETE /annotations/{id}/` → `204 No Content`.

Create request:

```json
{
  "document": 12,
  "label": 4,
  "start": 0,
  "end": 6
}
```

Правила:

- document и label должны принадлежать текущему пользователю;
- `start` и `end` — неотрицательные integer offsets;
- `start < end <= len(document.content)`;
- выделение не может состоять только из whitespace;
- `text` read-only и вычисляется как `document.content[start:end]`;
- пересечения и дубликаты backend не запрещает.

Поле модели `text` ограничено 500 символами. Serializer не проверяет эту длину до записи, поэтому клиенту не следует отправлять диапазон длиннее 500 символов.

## Ошибки

Типовые статусы:

| Status | Значение |
|---|---|
| `400` | validation error или неверные параметры |
| `401` | отсутствует/невалиден JWT |
| `404` | resource не существует или не принадлежит пользователю |
| `409` | label используется annotations |

Validation errors сгруппированы по полям в совместимом с прежним API формате:

```json
{
  "end": ["Конец выделения должен быть больше начала."]
}
```

Кастомные action errors используют `detail`, например:

```json
{"detail": "page and page_size must be integers."}
```

## Frontend contract

Frontend зависит от следующих деталей:

- JWT response содержит `access` и `refresh`;
- document create/update принимает `FormData`;
- chunk endpoint возвращает массив `chunk` и абсолютные offsets;
- annotation references используют числовые IDs;
- `text` annotation формирует backend;
- delete занятой label возвращает `code: label_in_use`;
- frontend export JSON строится в `frontend/src/utils/export.js`;
- backend export использует совместимую JSON schema v2.

Актуальная OpenAPI schema генерируется FastAPI на `/openapi.json`. При изменении контракта нужно синхронно обновить backend tests, frontend consumer/tests и этот guide; `backend/static/schema.yaml` сохранён для legacy Django backend.
