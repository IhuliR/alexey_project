# Инструкция для AI/Codex

## Источник истины

Сначала изучай фактический код и конфигурацию, затем документацию. Для API сверяй как минимум:

- `backend/api/urls.py`, `views.py`, `serializers.py`, `permissions.py`;
- `backend/core/models.py` и migrations;
- `backend/config/settings.py` и `config/urls.py`;
- `frontend/src/api/api.js` и затронутые pages/components;
- `.env.example`, Dockerfiles, `infra/docker-compose.yml`, Nginx и workflows;
- tests.

`backend/static/schema.yaml` используется ReDoc, но является статическим файлом и может отстать от кода. При конфликте код и tests имеют приоритет.

## Правила работы

- Не меняй стек, архитектуру, API или пользовательские сценарии без необходимости задачи.
- Не делай широкие refactor попутно; сохраняй тематические и минимальные patches.
- Сохраняй API compatibility. При намеренном изменении контракта синхронно обновляй backend, frontend, tests, `API_GUIDE.md` и OpenAPI schema.
- Не доверяй ownership-полям и тексту аннотации от клиента.
- Сохраняй isolation по пользователю для documents, labels и annotations.
- Учитывай, что offsets абсолютны относительно сохранённого `TextDocument.content`, а диапазон имеет вид `[start, end)`.
- Не добавляй secrets, реальные credentials, `.env`, дампы БД или build/runtime artifacts.
- Новые settings оформляй через environment и отражай безопасными placeholders в `.env.example`.
- Изменения моделей сопровождай migrations; не редактируй старые migrations без специальной задачи.
- Обновляй документацию вместе с поведением, не описывай планируемые возможности как реализованные.

## Критичные контракты

- Documents и labels принадлежат `request.user`; annotations — владельцу через `annotation.document.user`.
- Document create/update использует `multipart/form-data`.
- `Annotation.text` read-only и вычисляется backend по offsets.
- Document/label ownership и границы аннотации проверяются serializer.
- Удаление используемой label возвращает `409` и `code: label_in_use`.
- `documents/{id}/chunks/` возвращает массив `chunk` и абсолютные offsets; при `page_size > 1` единичные offsets равны `null`.
- Изменение `document.content` сейчас не пересчитывает существующие annotations.
- Export JSON реализован на frontend, отдельного backend endpoint нет.

## Проверка изменений

Запускай релевантный минимум и честно перечисляй результаты:

```bash
cd backend
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

В CI flake8 устанавливается отдельно и запускается для `backend/`.

```bash
cd frontend
CI=true npm test -- --watchAll=false
npm run build
```

Для документации дополнительно проверь локальные Markdown links, устаревшие формулировки и `git diff --check`. Не коммить изменения без прямого запроса.

## Итоговый отчёт

Укажи:

- изменённые файлы и поведение;
- выполненные и пропущенные проверки;
- изменение API-контракта либо его отсутствие;
- найденные проблемы, не входящие в задачу.
