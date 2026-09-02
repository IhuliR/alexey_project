import { Link } from 'react-router-dom';

function Footer() {
  return (
    <footer className="app-footer">
      <div className="footer-content">
        <div className="footer-summary">
          <p>
            Formaslov — приложение для загрузки исследовательских текстов,
            ручной разметки, пакетного импорта и экспорта результатов в JSON.
          </p>
          <p className="footer-stack">
            Python · FastAPI · SQLAlchemy · React · JWT · PostgreSQL · Redis · RabbitMQ · Celery · Docker · Nginx
          </p>
        </div>

        <div className="footer-meta">
          <nav className="footer-links" aria-label="Ссылки проекта">
            <Link to="/about">О проекте</Link>
            <Link to="/technologies">Технологии</Link>
            <a
              href="https://github.com/IhuliR"
              target="_blank"
              rel="noreferrer"
            >
              GitHub: IhuliR
            </a>
            <a
              href="https://github.com/IhuliR/formaslov"
              target="_blank"
              rel="noreferrer"
            >
              Репозиторий
            </a>
          </nav>
          <p className="footer-copyright">© 2026 IhuliR</p>
        </div>
      </div>
    </footer>
  );
}

export default Footer;
