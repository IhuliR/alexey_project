# Правила разработки Formaslov

Этот файл фиксирует только соглашения, связанные с текущей архитектурой и API-контрактом проекта.

## Границы изменений

- Сохраняйте разделение `core` (модели), `api` (HTTP layer), `users` (пользователь) и `config` (settings/routing).
- Не меняйте стек, JWT flow, модель пользователя, алгоритм chunking или формат frontend export без отдельной задачи.
- Избегайте широких refactor в изменениях, связанных с одной функцией или исправлением.

## Ownership и permissions

- Все querysets документов и меток фильтруются по `request.user`; аннотации — по `document__user=request.user`.
- Владелец документа или метки назначается backend и не принимается от клиента.
- Для аннотации проверяются оба объекта: document и label должны принадлежать текущему пользователю.
- Object permission учитывает структуру модели: `obj.user` либо `obj.document.user`.
- Не заменяйте queryset isolation одной object-level проверкой: фильтрация также предотвращает раскрытие чужих ID.

## Validation и offsets

- Валидация входного API-контракта размещается в serializer; ownership, зависящий от запроса, проверяется через serializer context.
- `Annotation.text` остаётся read-only и вычисляется как `document.content[start:end]`.
- Диапазон аннотации — `[start, end)`: `start >= 0`, `start < end`, `end <= len(content)`; whitespace-only фрагменты запрещены.
- Переносы строк новых/изменённых документов нормализуются в `LF`. Chunks и frontend должны использовать offsets исходного сохранённого `content`.
- Изменение chunk response требует одновременного обновления `DocumentPage`, тестов, `API_GUIDE.md` и `backend/static/schema.yaml`.
- При изменении редактирования документа отдельно решайте судьбу существующих аннотаций: сейчас их offsets не пересчитываются.

## API contract

- Сохраняйте префикс `/api/v1/` и используйте DRF router/actions.
- Documents create/update принимают `multipart/form-data`; labels и annotations обычно используют JSON.
- Для кастомных ошибок используйте `detail`; стабильные машинные сценарии дополняйте `code`, как `label_in_use`.
- Не меняйте HTTP method, content type или response shape без синхронного изменения frontend и документации.
- `API_GUIDE.md` и используемая ReDoc schema — две части одного контракта; обновляйте обе.

## Settings и данные

- Не добавляйте secrets, credentials, `.env`, локальные базы и build/runtime artifacts в Git.
- Новые настройки должны читаться из environment; безопасный пример добавляется в `.env.example`.
- PostgreSQL — единственный настроенный database backend. Не добавляйте неявный SQLite fallback.
- Любое изменение модели сопровождается migration. Перед завершением выполните `makemigrations --check --dry-run`.
- `.txt` сейчас хранится как текст в PostgreSQL, а не как media-файл; не документируйте файловое хранилище без реализации.

## Frontend/backend boundary

- Все HTTP-запросы идут через общий Axios client в `frontend/src/api/api.js`.
- JWT refresh и очистка tokens остаются централизованными.
- API URL задаётся через `REACT_APP_API_URL` на этапе запуска/сборки CRA.
- При изменении offsets, auth или response shape обновляйте зависящие components/pages и contract tests.
- Export JSON формируется в браузере; изменение его schema требует обновления frontend tests и документации.

## Проверки

Backend:

```bash
cd backend
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

CI отдельно устанавливает flake8 и запускает `python -m flake8 backend/` из корня репозитория.

Frontend:

```bash
cd frontend
CI=true npm test -- --watchAll=false
npm run build
```

Выбирайте проверки по затронутой области, но обязательно сообщайте, что запускалось. Изменения ownership, permissions, validation и migrations должны иметь regression tests.
