const AUTH_ERROR_MESSAGES = {
  'No active account found with the given credentials':
    'Неверное имя пользователя или пароль.',
};

export const getAuthErrorMessage = (error) => {
  const detail = error?.response?.data?.detail;

  if (detail) {
    return AUTH_ERROR_MESSAGES[detail] || detail;
  }

  return 'Произошла ошибка. Попробуйте ещё раз.';
};

export const getApiErrorMessage = (error, fallback = 'Произошла ошибка. Попробуйте ещё раз.') => {
  const detail = error?.response?.data?.detail;

  if (typeof detail === 'string' && detail.trim()) {
    return detail;
  }

  if (Array.isArray(detail) && detail.length > 0) {
    return detail
      .map((item) => item?.msg || item?.message || '')
      .filter(Boolean)
      .join('; ') || fallback;
  }

  if (error?.message) {
    return error.message;
  }

  return fallback;
};
