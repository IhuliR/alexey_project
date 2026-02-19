import { useEffect, useState } from 'react';
import api from '../api/api';
import ErrorMessage from '../components/ErrorMessage';
import Header from '../components/Header';
import Loader from '../components/Loader';

const getErrorMessage = (error) => {
  if (error?.response?.data) {
    return JSON.stringify(error.response.data);
  }
  return 'Network or server error';
};

function LabelsPage() {
  const [labels, setLabels] = useState([]);
  const [name, setName] = useState('');
  const [color, setColor] = useState('#ffff00');
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [deletingId, setDeletingId] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;

    const loadLabels = async () => {
      setLoading(true);
      setError('');

      try {
        const response = await api.get('labels/');
        if (!cancelled) {
          setLabels(Array.isArray(response.data) ? response.data : []);
        }
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

    loadLabels();

    return () => {
      cancelled = true;
    };
  }, []);

  const refreshLabels = async () => {
    const response = await api.get('labels/');
    setLabels(Array.isArray(response.data) ? response.data : []);
  };

  const handleCreate = async (event) => {
    event.preventDefault();
    setCreating(true);
    setError('');

    try {
      const response = await api.post('labels/', {
        name,
        color,
      });

      if (response.data) {
        setName('');
        setColor('#ffff00');
        await refreshLabels();
      }
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async (labelId) => {
    setDeletingId(labelId);
    setError('');

    try {
      await api.delete(`labels/${labelId}/`);
      await refreshLabels();
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <div className="page">
      <Header />
      <main className="container">
        <section className="card">
          <h1 className="page-title">Метки</h1>
          <form className="labels-form" onSubmit={handleCreate}>
            <label className="field">
              <span>Название</span>
              <input
                type="text"
                value={name}
                onChange={(event) => setName(event.target.value)}
                required
              />
            </label>
            <label className="field">
              <span>Цвет</span>
              <input
                type="color"
                value={color}
                onChange={(event) => setColor(event.target.value)}
              />
            </label>
            <button type="submit" className="btn" disabled={creating}>
              Добавить
            </button>
          </form>
          <ErrorMessage message={error} />
        </section>

        <section className="card">
          {loading ? (
            <Loader />
          ) : (
            <ul className="labels-list">
              {labels.map((label) => (
                <li key={label.id} className="labels-item">
                  <span className="label-name">{label.name}</span>
                  <span
                    className="label-swatch"
                    style={{ backgroundColor: label.color || '#ffff00' }}
                  />
                  <button
                    type="button"
                    className="btn danger small"
                    onClick={() => handleDelete(label.id)}
                    disabled={deletingId === label.id}
                  >
                    Удалить
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>
      </main>
    </div>
  );
}

export default LabelsPage;
