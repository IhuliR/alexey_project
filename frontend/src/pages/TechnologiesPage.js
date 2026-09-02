const technologies = [
  'Python',
  'FastAPI',
  'SQLAlchemy',
  'Pydantic',
  'PostgreSQL',
  'Alembic',
  'Redis',
  'RabbitMQ',
  'Celery',
  'React',
  'JWT',
  'Docker Compose',
  'Nginx',
  'GitHub Actions',
  'AI-assisted development',
];

function TechnologiesPage() {
  return (
    <main className="info-page">
      <section className="info-hero technologies-hero">
        <div className="info-hero-copy">
          <p className="eyebrow">Fullstack-разработка</p>
          <h1>Технологии и реализация</h1>
          <p className="info-lead">
            Formaslov — fullstack-проект с backend на FastAPI, frontend на
            React SPA, фоновой обработкой через Celery/RabbitMQ и
            инфраструктурой развёртывания на Docker Compose.
          </p>
          <div className="tech-badges" aria-label="Технологии проекта">
            {technologies.map((technology) => (
              <span key={technology}>{technology}</span>
            ))}
          </div>
        </div>
      </section>

      <section
        className="info-card-grid stack-overview"
        aria-label="Стек проекта"
      >
        <article className="info-card stack-card">
          <span className="feature-number">01</span>
          <h2>Backend</h2>
          <p>Python, FastAPI, SQLAlchemy, Pydantic, JWT, REST API и доменная модель данных.</p>
        </article>
        <article className="info-card stack-card">
          <span className="feature-number">02</span>
          <h2>Frontend</h2>
          <p>
            React SPA, маршрутизация, формы, разметка текста, import/export UI.
          </p>
        </article>
        <article className="info-card stack-card">
          <span className="feature-number">03</span>
          <h2>DevOps</h2>
          <p>
            PostgreSQL, Alembic, Redis, RabbitMQ, Celery, Docker Compose,
            Nginx и GitHub Actions.
          </p>
        </article>
      </section>

      <section className="info-section">
        <div className="info-section-heading">
          <p className="eyebrow">Серверная часть</p>
          <h2>Backend</h2>
        </div>
        <div className="info-prose">
          <p>
            Backend написан на{' '}
            <strong>Python, FastAPI, SQLAlchemy и Pydantic</strong>. Он отвечает
            за пользователей, документы, метки, аннотации, права доступа,
            пакетный импорт материалов и фоновый экспорт размеченных текстов.
          </p>
          <div className="info-card info-list-card">
            <ul className="info-check-list">
              <li>REST API для документов, меток, аннотаций, импорта и экспорта.</li>
              <li>JWT-аутентификация.</li>
              <li>Изоляция пользовательских данных.</li>
              <li>Ownership-проверки и пользовательские метки.</li>
              <li>
                Защита от удаления меток, которые используются в аннотациях.
              </li>
              <li>Пакетный ZIP-импорт <code>.txt</code>/<code>.docx</code>.</li>
              <li>Фоновый экспорт документа и разметки в JSON.</li>
              <li>
                Read-only demo-режим без доступа к реальным пользовательским
                данным.
              </li>
            </ul>
          </div>
          <p>
            Одна из важных backend-задач — аккуратно развести человекочитаемые
            и технические данные. У документа есть обычное название, которое
            видит пользователь, и технический <code>slug</code>, который
            генерируется автоматически. Например, документ «Тёзка» получает
            slug <code>tezka</code>, а при совпадениях система создаёт
            уникальные варианты: <code>tezka-2</code>, <code>tezka-3</code> и
            так далее. Это сохраняет нормальный пользовательский UX и даёт
            аккуратные имена файлов при экспорте, например{' '}
            <code>tezka_export.json</code>.
          </p>
        </div>
      </section>

      <section className="info-section">
        <div className="info-section-heading">
          <p className="eyebrow">Предметная область</p>
          <h2>API и модель данных</h2>
        </div>
        <div className="entity-grid">
          <article className="entity-card">
            <code>User</code>
            <p>Владелец данных</p>
          </article>
          <article className="entity-card">
            <code>Document</code>
            <p>Текстовый документ</p>
          </article>
          <article className="entity-card">
            <code>Label</code>
            <p>Пользовательская метка</p>
          </article>
          <article className="entity-card">
            <code>Annotation</code>
            <p>Размеченный фрагмент текста</p>
          </article>
        </div>
        <div className="info-prose">
          <p>
            Для аннотации важна связка{' '}
            <code>document + label + start/end + selected text</code>. Backend
            проверяет, что аннотация создаётся внутри доступного документа и
            использует доступную пользователю метку. Это защищает данные не
            только на уровне интерфейса, но и при прямом обращении к API.
          </p>
          <p>
            Отдельно проработана обработка ошибок. Например, если пользователь
            пытается удалить метку, которая уже используется в аннотациях,
            backend возвращает понятный <code>409 Conflict</code>, а frontend
            показывает нормальное сообщение вместо технической ошибки.
          </p>
        </div>
      </section>

      <section className="info-section">
        <div className="info-section-heading">
          <p className="eyebrow">Клиентская часть</p>
          <h2>Frontend</h2>
        </div>
        <div className="info-prose">
          <p>
            Frontend реализован как <strong>React SPA</strong>. Он отвечает за
            клиентскую маршрутизацию, авторизацию, формы, работу с документами,
            визуальную разметку текста, запуск пакетного импорта и скачивание
            готового экспорта.
          </p>
          <div className="info-card info-list-card">
            <ul className="info-check-list">
              <li>Публичная главная страница и read-only demo.</li>
              <li>Регистрация, вход и смена пароля.</li>
              <li>Защищённые страницы документов и меток.</li>
              <li>Общий header и footer.</li>
              <li>
                Загрузка <code>.txt</code> файлов и создание документов.
              </li>
              <li>Пакетный ZIP-импорт материалов через фоновую обработку.</li>
              <li>Создание меток и выделение фрагментов текста.</li>
              <li>Подсветка аннотаций и фоновый экспорт JSON.</li>
            </ul>
          </div>
          <div className="info-callout">
            Для приложения разметки важно, чтобы визуально выбранный фрагмент
            точно совпадал с сохранёнными <code>start</code>, <code>end</code>{' '}
            и <code>text</code>: от этого зависит корректность последующего
            экспорта и анализа.
          </div>
        </div>
      </section>

      <section className="info-section">
        <div className="info-section-heading">
          <p className="eyebrow">Инфраструктура</p>
          <h2>DevOps</h2>
        </div>
        <div className="info-prose">
          <p>
            Backend запускается как FastAPI-сервис, Nginx используется как
            reverse proxy и сервер статики, Redis отвечает за кэш, RabbitMQ —
            за очередь задач, а Celery worker выполняет импорт и экспорт. Для
            автоматизации проверок и деплоя настроен CI/CD через GitHub
            Actions.
          </p>
          <div className="info-card info-list-card">
            <ul className="info-check-list">
              <li>Отдельный backend-сервис на FastAPI.</li>
              <li>Alembic migrations для PostgreSQL.</li>
              <li>Redis cache layer.</li>
              <li>RabbitMQ broker и Celery worker.</li>
              <li>Сборка frontend в статические файлы.</li>
              <li>Nginx как reverse proxy и сервер для frontend/static.</li>
              <li>Docker Compose для оркестрации сервисов.</li>
              <li>Volumes для статики, media-файлов и данных.</li>
              <li>Переменные окружения для настроек приложения.</li>
              <li>CI/CD через GitHub Actions.</li>
            </ul>
          </div>
          <p>
            Такая структура позволяет запускать проект локально,
            воспроизводимо разворачивать его на сервере и отделять код
            приложения от окружения, секретов и пользовательских данных.
          </p>
        </div>
      </section>

      <section className="info-section ai-section">
        <div className="info-section-heading">
          <p className="eyebrow">Инженерный процесс</p>
          <h2>Работа с AI-инструментами</h2>
        </div>
        <div className="info-prose">
          <p>
            Backend-часть, архитектуру API, модель данных и серверную
            бизнес-логику я проектировал и реализовывал самостоятельно.
            Frontend и часть интеграционных задач разрабатывались с
            использованием Codex и ChatGPT в управляемом AI-assisted workflow.
          </p>
          <div className="workflow-grid">
            <article className="workflow-card">
              <h3>Постановка задач</h3>
              <p>
                Метапромптинг и точные промпты с контекстом, ограничениями,
                критериями проверки и ожидаемым результатом.
              </p>
            </article>
            <article className="workflow-card">
              <h3>Документирующая база</h3>
              <p>
                <code>ARCHITECTURE.md</code>, <code>API_GUIDE.md</code>,{' '}
                <code>STYLE_GUIDE.md</code> и <code>AGENTS.md</code> задают
                рабочий контекст для ИИ-ассистента.
              </p>
            </article>
            <article className="workflow-card">
              <h3>Контроль изменений</h3>
              <p>
                Ручное ревью diff’ов, traceback’ов и пользовательских сценариев,
                а также отдельные regression-fix задачи.
              </p>
            </article>
            <article className="workflow-card">
              <h3>Архитектурная ответственность</h3>
              <p>
                Разделение изменений на небольшие коммиты и финальные
                технические решения на стыке frontend и backend.
              </p>
            </article>
          </div>
          <div className="info-callout">
            ИИ использовался как профессиональный инструмент ускорения
            разработки, при сохранении контроля над архитектурой,
            backend-логикой, моделью данных и продуктовыми решениями.
          </div>
        </div>
      </section>

      <section className="info-section">
        <div className="info-section-heading">
          <p className="eyebrow">Результат</p>
          <h2>Что показывает проект</h2>
        </div>
        <div className="info-closing">
          <p>
            Formaslov показывает умение развивать приложение как продукт:
            выделять предметную область, проектировать API и модель данных,
            продумывать права доступа, связывать frontend и backend, работать с
            асинхронным импортом/экспортом данных и разворачивать
            fullstack-приложение в контейнерах.
          </p>
          <p>
            Отдельно проект демонстрирует навык осмысленной работы с
            AI-инструментами: постановку технических задач, подготовку
            проектной документации, контроль изменений, ревью результата и
            использование нейросетей как профессионального инструмента.
          </p>
          <strong>
            Текущая версия остаётся MVP, но уже закрывает полный базовый
            сценарий: зарегистрироваться, загрузить материалы, создать метки,
            разметить фрагменты и получить JSON-экспорт для дальнейшего
            анализа.
          </strong>
        </div>
      </section>
    </main>
  );
}

export default TechnologiesPage;
