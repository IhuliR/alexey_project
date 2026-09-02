import { getApiErrorMessage, getAuthErrorMessage } from './apiErrors';

test('maps invalid credentials auth error to user-friendly message', () => {
  expect(
    getAuthErrorMessage({
      response: {
        data: {
          detail: 'No active account found with the given credentials',
        },
      },
    })
  ).toBe('Неверное имя пользователя или пароль.');
});

test('returns unknown auth detail as fallback message', () => {
  expect(
    getAuthErrorMessage({
      response: {
        data: {
          detail: 'Custom auth error',
        },
      },
    })
  ).toBe('Custom auth error');
});

test('returns generic auth error when detail is missing', () => {
  expect(getAuthErrorMessage({ response: { data: {} } })).toBe(
    'Произошла ошибка. Попробуйте ещё раз.'
  );
});

test('returns safe API detail messages', () => {
  expect(
    getApiErrorMessage({
      response: {
        data: {
          detail: 'Только .zip файлы разрешены.',
        },
      },
    })
  ).toBe('Только .zip файлы разрешены.');
});

test('maps validation API details to a compact message', () => {
  expect(
    getApiErrorMessage({
      response: {
        data: {
          detail: [
            { msg: 'Field required' },
            { message: 'Invalid value' },
          ],
        },
      },
    })
  ).toBe('Field required; Invalid value');
});
