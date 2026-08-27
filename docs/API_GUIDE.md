# API guide

## Общая информация

- Base URL: `/api/v1/`
- Основной формат: JSON
- Documents create/update: `multipart/form-data`
- Auth header: `Authorization: Bearer <access_token>`
- По умолчанию API требует аутентификацию; исключения — регистрация и JWT endpoints.

Все documents, labels и annotations изолированы по текущему пользователю. Чужой detail resource обычно выглядит как отсутствующий и возвращает `404 Not Found`.

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

DRF validation errors обычно сгруппированы по полям:

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
- export JSON строится в `frontend/src/utils/export.js`; backend export endpoint отсутствует.

При изменении контракта нужно синхронно обновить backend tests, frontend consumer/tests, этот guide и `backend/static/schema.yaml`.
