import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api/api';
import ErrorMessage from '../components/ErrorMessage';
import Loader from '../components/Loader';

function LoginPage() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    if (localStorage.getItem('access_token')) {
      navigate('/documents', { replace: true });
    }
  }, [navigate]);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setIsLoading(true);
    setError('');

    try {
      const response = await api.post('jwt/create/', {
        username,
        password,
      });

      const { access, refresh } = response.data || {};

      // Не привязываемся к status (бэк может вернуть 200 или 201),
      // проверяем наличие токенов в ответе.
      if (!access || !refresh) {
        setError('Server response missing access/refresh token');
        return;
      }

      localStorage.setItem('access_token', access);
      localStorage.setItem('refresh_token', refresh);
      navigate('/documents', { replace: true });
    } catch (requestError) {
      if (requestError.response?.data) {
        setError(JSON.stringify(requestError.response.data));
      } else {
        setError('Network or server error');
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <main className="auth-page">
      <form className="auth-form" onSubmit={handleSubmit}>
        <h1>Login</h1>

        <label htmlFor="username">Username</label>
        <input
          id="username"
          type="text"
          value={username}
          onChange={(event) => setUsername(event.target.value)}
          required
        />

        <label htmlFor="password">Password</label>
        <input
          id="password"
          type="password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          required
        />

        <button type="submit" className="btn" disabled={isLoading}>
          {isLoading ? 'Signing in...' : 'Sign In'}
        </button>

        {isLoading && <Loader />}
        <ErrorMessage message={error} />
      </form>
    </main>
  );
}

export default LoginPage;
