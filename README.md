# Text Annotation API + React Frontend (MVP)

Этот MVP реализует полный сценарий разметки текста с аутентификацией.
Пользователь может создавать документы вручную или загружать `.txt` файлы.
Просмотр документа построен на фрагментах (chunks), а разметка выполняется метками по выделенным диапазонам текста.
Фронтенд поддерживает экспорт аннотаций и метаданных в локальный JSON-файл.

## Технологический стек

- Python + Django + Django REST Framework
- JWT-аутентификация через Djoser
- React (Create React App)
- Axios (с JWT-интерсепторами)

## Требования

- Python 3.12+
- Node.js 18+ (рекомендуется LTS)

## Установка и запуск (локально)

### A) Бэкенд

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cd alexey_project/
python manage.py migrate
python manage.py runserver
```

Базовый URL API:

```text
http://127.0.0.1:8000/api/v1/
```

### B) Фронтенд

```bash
cd frontend/
npm install
npm start
```

URL интерфейса:

```text
http://localhost:3000
```

## Аутентификация

- Используйте страницу входа в интерфейсе.
- JWT-эндпоинты (для справки):
  - `POST /api/v1/jwt/create/`
  - `POST /api/v1/jwt/refresh/`

## Чеклист MVP

- Вход в систему
- Создание документа
- Загрузка `.txt` (`documents/upload/`)
- Навигация по фрагментам на странице документа (`documents/{id}/chunks/?page=&page_size=1`)
- Создание меток
- Создание/удаление аннотаций
- Экспорт JSON со страницы документа

## Устранение неполадок

- CORS: бэкенд должен разрешать `http://localhost:3000`.
- Если вход не работает: проверьте, что бэкенд запущен и учетные данные существуют.
- Если UI показывает `Network or server error`: откройте DevTools -> Network и проверьте HTTP-статусы.

## Лицензия

Лицензия MIT.
