import axios from 'axios';
import {
  clearTokens,
  getAccessToken,
  getRefreshToken,
  saveAccessToken,
} from '../auth/tokenStorage';

const baseURL =
  process.env.REACT_APP_API_URL || '/api/v1/';

const api = axios.create({ baseURL });
const authApi = axios.create({ baseURL });

let unauthorizedHandler = null;

export const setUnauthorizedHandler = (handler) => {
  unauthorizedHandler = handler;
};

const handleUnauthorized = () => {
  clearTokens();
  if (unauthorizedHandler) {
    unauthorizedHandler();
    return;
  }
  window.location.assign('/login');
};

api.interceptors.request.use((config) => {
  const accessToken = getAccessToken();
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

    if (error.response.status === 401 && !originalRequest) {
      handleUnauthorized();
      return Promise.reject(error);
    }

    if (error.response.status === 401 && originalRequest?._retry) {
      handleUnauthorized();
      return Promise.reject(error);
    }

    if (error.response.status === 401 && !originalRequest?._retry) {
      originalRequest._retry = true;
      const refreshToken = getRefreshToken();

      if (!refreshToken) {
        handleUnauthorized();
        return Promise.reject(error);
      }

      try {
        const refreshResponse = await authApi.post('jwt/refresh/', {
          refresh: refreshToken,
        });
        const access = refreshResponse.data?.access;

        if (!access) {
          handleUnauthorized();
          return Promise.reject(error);
        }

        saveAccessToken(access);
        originalRequest.headers.Authorization = `Bearer ${access}`;
        return api(originalRequest);
      } catch (refreshError) {
        handleUnauthorized();
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);

export const createTokenPair = async (username, password) => {
  const response = await authApi.post('jwt/create/', { username, password });
  const { access, refresh } = response.data || {};

  if (!access || !refresh) {
    throw new Error('Сервер не вернул JWT-токены.');
  }

  return { access, refresh };
};

export const verifyAccessToken = (token) =>
  authApi.post('jwt/verify/', { token });

export const refreshAccessToken = async (refresh) => {
  const response = await authApi.post('jwt/refresh/', { refresh });
  const access = response.data?.access;

  if (!access) {
    throw new Error('Сервер не вернул новый access-токен.');
  }

  return access;
};

export const registerUser = (username, password) =>
  authApi.post('users/', { username, password });

export const getCurrentUser = async () => {
  const response = await api.get('users/me/');
  return response.data;
};

export const changePassword = (passwords) =>
  api.post('users/set_password/', passwords);

export const createImportBatch = (file) => {
  const formData = new FormData();
  formData.append('file', file);
  return api.post('imports/', formData);
};

export const getImportBatch = (id) =>
  api.get(`imports/${id}/`);

export const getImportItems = (id) =>
  api.get(`imports/${id}/items/`);

export const createExportJob = (documentId, format = 'json') =>
  api.post('exports/', {
    document_id: documentId,
    format,
  });

export const getExportJob = (id) =>
  api.get(`exports/${id}/`);

export const downloadExportJob = (id) =>
  api.get(`exports/${id}/download/`, {
    responseType: 'blob',
  });

export default api;
