import axios from 'axios';

const api = axios.create({
  baseURL: 'http://127.0.0.1:8000/api/v1/',
});

const redirectToLogin = () => {
  window.location.href = '/login';
};

api.interceptors.request.use((config) => {
  const accessToken = localStorage.getItem('access_token');
  if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (!error.response) {
      return Promise.reject(new Error('Network error. Please check your connection and try again.'));
    }

    const originalRequest = error.config;

    if (error.response.status === 401 && !originalRequest?._retry) {
      originalRequest._retry = true;
      const refreshToken = localStorage.getItem('refresh_token');

      if (!refreshToken) {
        localStorage.clear();
        redirectToLogin();
        return Promise.reject(error);
      }

      try {
        const refreshResponse = await api.post('jwt/refresh/', {
          refresh: refreshToken,
        });

        if (refreshResponse.status === 201 && refreshResponse.data?.access) {
          localStorage.setItem('access_token', refreshResponse.data.access);
          return api(originalRequest);
        }

        localStorage.clear();
        redirectToLogin();
        return Promise.reject(error);
      } catch (refreshError) {
        localStorage.clear();
        redirectToLogin();
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);

export default api;
