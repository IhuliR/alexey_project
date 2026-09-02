import { useEffect, useRef, useState } from 'react';
import {
  createImportBatch,
  getImportBatch,
  getImportItems,
} from '../api/api';
import { getApiErrorMessage } from '../utils/apiErrors';
import ErrorMessage from './ErrorMessage';

const POLLING_INTERVAL = 2500;
const TERMINAL_STATUSES = new Set(['completed', 'completed_with_errors', 'failed']);

const getStatusText = (batch) => {
  if (!batch) {
    return '';
  }

  const processed = Number(batch.files_processed) || 0;
  const failed = Number(batch.files_failed) || 0;
  const total = Number(batch.files_total) || 0;
  const progress = total > 0
    ? `Обработано ${processed + failed} из ${total} файлов`
    : 'Архив ожидает обработки';

  if (batch.status === 'completed') {
    return `${progress}. Импорт завершен.`;
  }
  if (batch.status === 'completed_with_errors') {
    return `${progress}. Импорт завершен с ошибками.`;
  }
  if (batch.status === 'failed') {
    return batch.error || 'Импорт завершился ошибкой.';
  }
  if (batch.status === 'processing') {
    return progress;
  }
  return 'Архив поставлен в очередь.';
};

function BatchImportForm({ onCompleted }) {
  const fileInputRef = useRef(null);
  const notifiedBatchIdRef = useRef(null);
  const [selectedFile, setSelectedFile] = useState(null);
  const [batch, setBatch] = useState(null);
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [pollingError, setPollingError] = useState('');
  const [error, setError] = useState('');

  const isTerminal = batch ? TERMINAL_STATUSES.has(batch.status) : false;

  useEffect(() => {
    if (!batch?.id || isTerminal) {
      return undefined;
    }

    let cancelled = false;
    const timeoutId = window.setTimeout(async () => {
      try {
        const response = await getImportBatch(batch.id);
        if (cancelled) {
          return;
        }
        setBatch(response.data || null);
        setPollingError('');
      } catch (requestError) {
        if (!cancelled) {
          setPollingError(getApiErrorMessage(
            requestError,
            'Не удалось получить статус импорта.'
          ));
        }
      }
    }, POLLING_INTERVAL);

    return () => {
      cancelled = true;
      window.clearTimeout(timeoutId);
    };
  }, [batch, isTerminal]);

  useEffect(() => {
    if (!batch?.id || !isTerminal) {
      return undefined;
    }

    let cancelled = false;
    const loadItems = async () => {
      try {
        const response = await getImportItems(batch.id);
        if (!cancelled) {
          setItems(Array.isArray(response.data) ? response.data : []);
        }
      } catch (requestError) {
        if (!cancelled) {
          setPollingError(getApiErrorMessage(
            requestError,
            'Не удалось получить результаты импорта.'
          ));
        }
      }
    };

    loadItems();

    if (
      (batch.status === 'completed' || batch.status === 'completed_with_errors') &&
      notifiedBatchIdRef.current !== batch.id
    ) {
      notifiedBatchIdRef.current = batch.id;
      onCompleted?.();
    }

    return () => {
      cancelled = true;
    };
  }, [batch?.id, batch?.status, isTerminal, onCompleted]);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError('');
    setPollingError('');
    setItems([]);

    if (!selectedFile) {
      setError('Выберите ZIP-архив');
      return;
    }

    if (!selectedFile.name.toLowerCase().endsWith('.zip')) {
      setError('Поддерживаются только .zip архивы');
      return;
    }

    setLoading(true);

    try {
      const response = await createImportBatch(selectedFile);
      setBatch(response.data || null);
      setSelectedFile(null);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, 'Не удалось отправить архив.'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <form className="form-grid batch-import-form" onSubmit={handleSubmit}>
      <label className="field">
        <span>ZIP-архив с TXT/DOCX</span>
        <input
          ref={fileInputRef}
          type="file"
          accept=".zip,application/zip"
          onChange={(event) => {
            setSelectedFile(event.target.files?.[0] || null);
            setError('');
          }}
        />
      </label>
      <div className="actions-row">
        <button type="submit" className="btn secondary" disabled={loading}>
          {loading ? 'Отправка...' : 'Импортировать ZIP'}
        </button>
      </div>

      {batch ? (
        <div className="job-status">
          <p>{getStatusText(batch)}</p>
          {items.length > 0 ? (
            <ul className="job-result-list">
              {items.map((item) => (
                <li key={item.id}>
                  <span>{item.status === 'processed' ? 'Готово' : 'Ошибка'}</span>
                  {' '}
                  {item.filename}
                  {item.error ? ` - ${item.error}` : ''}
                </li>
              ))}
            </ul>
          ) : null}
        </div>
      ) : null}

      <ErrorMessage message={error || pollingError} />
    </form>
  );
}

export default BatchImportForm;
