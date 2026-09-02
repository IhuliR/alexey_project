import { Link } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';

function LandingPage() {
  const { isAuthenticated, isLoading } = useAuth();

  return (
    <main className="landing-page">
      <section className="landing-hero">
        <p className="eyebrow">Ручная разметка текстов</p>
        <h1>Formaslov</h1>
        <p className="landing-lead">
          Загружайте тексты вручную или ZIP-архивом, выделяйте фрагменты,
          назначайте им метки и экспортируйте готовую разметку в JSON.
        </p>
        <div className="landing-actions">
          {isAuthenticated && !isLoading ? (
            <>
              <Link to="/documents" className="btn button-link">
                Перейти к документам
              </Link>
              <Link to="/demo" className="btn ghost button-link">
                Посмотреть демо
              </Link>
            </>
          ) : (
            <>
              <Link to="/demo" className="btn button-link">
                Попробовать демо
              </Link>
              <Link to="/register" className="btn secondary button-link">
                Создать аккаунт
              </Link>
            </>
          )}
        </div>
      </section>

      <section className="feature-grid" aria-label="Возможности Formaslov">
        <article className="feature-card">
          <span className="feature-number">01</span>
          <h2>Загрузите материалы</h2>
          <p>Создайте документ вручную, выберите .txt или импортируйте ZIP с .txt/.docx.</p>
        </article>
        <article className="feature-card">
          <span className="feature-number">02</span>
          <h2>Разметьте фрагменты</h2>
          <p>Выделяйте нужные части текста и назначайте им цветные метки.</p>
        </article>
        <article className="feature-card">
          <span className="feature-number">03</span>
          <h2>Экспортируйте результат</h2>
          <p>Запускайте JSON-экспорт и скачивайте готовый файл после обработки.</p>
        </article>
      </section>
    </main>
  );
}

export default LandingPage;
