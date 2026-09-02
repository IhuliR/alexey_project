import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../api/api';
import BatchImportForm from '../components/BatchImportForm';
import DocumentForm from '../components/DocumentForm';
import ErrorMessage from '../components/ErrorMessage';
import Loader from '../components/Loader';
import Pagination from '../components/Pagination';

const LIMIT = 10;

const getErrorMessage = (error) => {
  if (error?.response?.data) {
    return JSON.stringify(error.response.data);
  }
  return 'Network or server error';
};

function DocumentsPage() {
  const [documents, setDocuments] = useState([]);
  const [offset, setOffset] = useState(0);
  const [count, setCount] = useState(0);
  const [hasNext, setHasNext] = useState(false);
  const [hasPrev, setHasPrev] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [reloadToken, setReloadToken] = useState(0);

  useEffect(() => {
    let cancelled = false;

    const loadDocuments = async () => {
      setLoading(true);
      setError('');

      try {
        const response = await api.get('documents/', {
          params: { limit: LIMIT, offset },
        });

        if (cancelled) {
          return;
        }

        const data = response.data || {};
        setDocuments(Array.isArray(data.results) ? data.results : []);
        setCount(typeof data.count === 'number' ? data.count : 0);
        setHasNext(Boolean(data.next));
        setHasPrev(Boolean(data.previous));
      } catch (requestError) {
        if (!cancelled) {
          setError(getErrorMessage(requestError));
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    loadDocuments();

    return () => {
      cancelled = true;
    };
  }, [offset, reloadToken]);

  const handleCreated = useCallback(() => {
    setReloadToken((prev) => prev + 1);
  }, []);

  const shownCount = Math.min(count, offset + documents.length);

  return (
    <div className="page">
      <main className="container">
        <section className="card">
          <h1 className="page-title">Документы</h1>
          <DocumentForm onCreated={handleCreated} />
          <div className="form-divider" />
          <BatchImportForm onCompleted={handleCreated} />
          <ErrorMessage message={error} />
        </section>

        <section className="card">
          {loading ? (
            <Loader />
          ) : (
            <>
              <ul className="document-list">
                {documents.map((doc) => {
                  const title = doc.title || 'Новый документ';
                  const createdAt = doc.created_at
                    ? new Date(doc.created_at).toLocaleDateString('ru-RU')
                    : '—';
                  const metadata = [doc.slug, createdAt]
                    .filter(Boolean)
                    .join(' · ');

                  return (
                    <li key={doc.id} className="document-list-item">
                      <Link to={`/documents/${doc.id}`} className="document-link">
                        {title}
                      </Link>
                      <p className="document-meta">{metadata}</p>
                    </li>
                  );
                })}
              </ul>

              <Pagination
                hasNext={hasNext}
                hasPrev={hasPrev}
                onNext={() => setOffset((prev) => prev + LIMIT)}
                onPrev={() => setOffset((prev) => Math.max(0, prev - LIMIT))}
                indicator={`Показано ${shownCount} из ${count}`}
              />
            </>
          )}
        </section>
      </main>
    </div>
  );
}

export default DocumentsPage;
