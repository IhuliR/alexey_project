import { render, screen } from '@testing-library/react';
import App from './App';

test('renders login page when no token exists', () => {
  render(<App />);
  expect(screen.getByRole('heading', { name: /login/i })).toBeInTheDocument();
});
