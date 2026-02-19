import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../api/api';
import DocumentForm from '../components/DocumentForm';
import ErrorMessage from '../components/ErrorMessage';
import Header from '../components/Header';
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
  const fileInputRef = useRef(null);
  const [documents, setDocuments] = useState([]);
  const [offset, setOffset] = useState(0);
  const [count, setCount] = useState(0);
  const [hasNext, setHasNext] = useState(false);
  const [hasPrev, setHasPrev] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [reloadToken, setReloadToken] = useState(0);
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState('');
  const [uploadSuccess, setUploadSuccess] = useState('');

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

  const handleCreated = () => {
    setReloadToken((prev) => prev + 1);
  };

  const handleUpload = async () => {
    setUploadError('');
    setUploadSuccess('');

    if (!selectedFile) {
      setUploadError('Выберите .txt файл');
      return;
    }

    if (!selectedFile.name.toLowerCase().endsWith('.txt')) {
      setUploadError('Поддерживаются только .txt файлы');
      return;
    }

    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', selectedFile);

      const response = await api.post('documents/upload/', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      if (response.status === 201 && response.data?.id) {
        setSelectedFile(null);
        if (fileInputRef.current) {
          fileInputRef.current.value = '';
        }
        setUploadSuccess('Файл успешно загружен');
        setReloadToken((prev) => prev + 1);
      } else {
        setUploadError('Не удалось загрузить файл');
      }
    } catch (requestError) {
      setUploadError(getErrorMessage(requestError));
    } finally {
      setUploading(false);
    }
  };

  const shownCount = Math.min(count, offset + documents.length);

  return (
    <div className="page">
      <Header />
      <main className="container">
        <section className="card">
          <h1 className="page-title">Документы</h1>
          <div className="upload-block">
            <p className="upload-title">Upload .txt</p>
            <div className="upload-controls">
              <input
                ref={fileInputRef}
                type="file"
                accept=".txt,text/plain"
                onChange={(event) => {
                  const file = event.target.files?.[0] || null;
                  setSelectedFile(file);
                  setUploadError('');
                  setUploadSuccess('');
                }}
              />
              <button type="button" className="btn" onClick={handleUpload} disabled={uploading}>
                Upload
              </button>
            </div>
            {uploading ? <Loader /> : null}
            {uploadError ? <p className="error-message">{uploadError}</p> : null}
            {uploadSuccess ? <p className="success-message">{uploadSuccess}</p> : null}
          </div>
          <DocumentForm onCreated={handleCreated} />
          <ErrorMessage message={error} />
        </section>

        <section className="card">
          {loading ? (
            <Loader />
          ) : (
            <>
              <ul className="document-list">
                {documents.map((doc) => {
                  const title = doc.title || `Документ #${doc.id}`;
                  const createdAt = doc.created_at
                    ? new Date(doc.created_at).toLocaleString()
                    : '—';

                  return (
                    <li key={doc.id} className="document-list-item">
                      <Link to={`/documents/${doc.id}`} className="document-link">
                        {title}
                      </Link>
                      <p className="document-meta">Создан: {createdAt}</p>
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
