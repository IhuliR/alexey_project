import { fireEvent, render, screen } from '@testing-library/react';
import App from './App';

beforeEach(() => {
  localStorage.clear();
  window.history.pushState({}, '', '/');
});

test('renders the public landing page with primary actions', async () => {
  render(<App />);

  expect(
    await screen.findByRole('heading', { name: 'Formaslov' })
  ).toBeInTheDocument();
  expect(screen.getByRole('link', { name: 'Formaslov' })).toHaveAttribute(
    'href',
    '/'
  );
  expect(
    screen.getByRole('link', { name: 'Попробовать демо' })
  ).toHaveAttribute('href', '/demo');
  expect(
    await screen.findByRole('link', { name: 'Зарегистрироваться' })
  ).toHaveAttribute('href', '/register');
  expect(screen.getByRole('link', { name: 'Войти' })).toHaveAttribute(
    'href',
    '/login'
  );
  expect(screen.getByRole('contentinfo')).toHaveTextContent(
    'пакетного импорта и экспорта результатов'
  );
  expect(screen.getByRole('link', { name: 'Репозиторий' })).toHaveAttribute(
    'href',
    'https://github.com/IhuliR/formaslov'
  );
});

test('opens a static read-only demo without creating auth tokens', async () => {
  render(<App />);

  fireEvent.click(
    await screen.findByRole('link', { name: 'Попробовать демо' })
  );

  expect(
    await screen.findByRole('heading', {
      name: 'Демо: путешествие по Петербургу',
    })
  ).toBeInTheDocument();
  expect(
    screen.getByText('Демо-режим только для просмотра.')
  ).toBeInTheDocument();
  expect(
    screen.getByRole('button', { name: 'Скачать пример JSON' })
  ).toBeInTheDocument();
  expect(document.querySelector('form')).not.toBeInTheDocument();
  expect(localStorage.getItem('access_token')).toBeNull();
  expect(localStorage.getItem('refresh_token')).toBeNull();
});

test('opens the public about page and exposes shared navigation links', async () => {
  window.history.pushState({}, '', '/about');
  render(<App />);

  expect(
    await screen.findByRole('heading', { name: 'О проекте', level: 1 })
  ).toBeInTheDocument();
  expect(
    screen.getByRole('heading', { name: 'Что уже умеет MVP' })
  ).toBeInTheDocument();

  const header = screen.getByRole('banner');
  expect(header).toContainElement(
    screen.getAllByRole('link', { name: 'Технологии' })[0]
  );
  expect(header).toContainElement(screen.getByRole('link', { name: 'Демо' }));

  const footer = screen.getByRole('contentinfo');
  expect(footer).toContainElement(
    screen.getAllByRole('link', { name: 'О проекте' })[1]
  );
});

test('opens the public technologies page without authentication', async () => {
  window.history.pushState({}, '', '/technologies');
  render(<App />);

  expect(
    await screen.findByRole('heading', {
      name: 'Технологии и реализация',
      level: 1,
    })
  ).toBeInTheDocument();
  expect(
    screen.getByRole('heading', { name: 'Работа с AI-инструментами' })
  ).toBeInTheDocument();
  expect(screen.getByText('FastAPI')).toBeInTheDocument();
  expect(localStorage.getItem('access_token')).toBeNull();
});

test('redirects an unauthenticated user from documents to login', async () => {
  window.history.pushState({}, '', '/documents');
  render(<App />);

  expect(
    await screen.findByRole('heading', { name: 'Вход' })
  ).toBeInTheDocument();
  expect(screen.getByRole('link', { name: 'Formaslov' })).toHaveAttribute(
    'href',
    '/'
  );
  expect(screen.getByRole('contentinfo')).toBeInTheDocument();
});

test('redirects an unauthenticated user from account to login', async () => {
  window.history.pushState({}, '', '/account');
  render(<App />);

  expect(
    await screen.findByRole('heading', { name: 'Вход' })
  ).toBeInTheDocument();
});

test('registration form rejects different passwords', async () => {
  window.history.pushState({}, '', '/register');
  render(<App />);

  fireEvent.change(await screen.findByLabelText('Имя пользователя'), {
    target: { value: 'new-user' },
  });
  fireEvent.change(screen.getByLabelText('Пароль'), {
    target: { value: 'first-password' },
  });
  fireEvent.change(screen.getByLabelText('Повторите пароль'), {
    target: { value: 'second-password' },
  });
  fireEvent.click(
    screen.getByRole('button', { name: 'Зарегистрироваться' })
  );

  expect(await screen.findByText('Пароли не совпадают.')).toBeInTheDocument();
});
