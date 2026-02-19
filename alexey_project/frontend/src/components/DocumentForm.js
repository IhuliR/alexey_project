import { useState } from 'react';
import api from '../api/api';
import ErrorMessage from './ErrorMessage';

const getErrorMessage = (error) => {
  if (error?.response?.data) {
    return JSON.stringify(error.response.data);
  }
  return 'Network or server error';
};

function DocumentForm({ onCreated }) {
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (event) => {
    event.preventDefault();
    setLoading(true);
    setError('');

    try {
      const formData = new FormData();
      formData.append('title', title);
      formData.append('content', content);

      const response = await api.post('documents/', formData);
      if (response.data) {
        setTitle('');
        setContent('');
        if (typeof onCreated === 'function') {
          onCreated();
        }
      }
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setLoading(false);
    }
  };

  return (
    <form className="form-grid" onSubmit={handleSubmit}>
      <label className="field">
        <span>Название (опционально)</span>
        <input type="text" value={title} onChange={(event) => setTitle(event.target.value)} />
      </label>
      <label className="field">
        <span>Содержимое</span>
        <textarea
          value={content}
          onChange={(event) => setContent(event.target.value)}
          rows={5}
          required
        />
      </label>
      <div className="actions-row">
        <button type="submit" className="btn" disabled={loading}>
          Создать
        </button>
      </div>
      <ErrorMessage message={error} />
    </form>
  );
}

export default DocumentForm;
