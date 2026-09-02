import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {
  createImportBatch,
  getImportBatch,
  getImportItems,
} from '../api/api';
import BatchImportForm from './BatchImportForm';

jest.mock('../api/api', () => ({
  createImportBatch: jest.fn(),
  getImportBatch: jest.fn(),
  getImportItems: jest.fn(),
}));

beforeEach(() => {
  jest.useFakeTimers();
  createImportBatch.mockReset();
  getImportBatch.mockReset();
  getImportItems.mockReset();
  getImportItems.mockResolvedValue({ data: [] });
});

afterEach(() => {
  jest.clearAllTimers();
  jest.useRealTimers();
});

test('uploads ZIP and polls import status until completion', async () => {
  const onCompleted = jest.fn();
  createImportBatch.mockResolvedValue({
    data: {
      id: 3,
      status: 'pending',
      files_total: 0,
      files_processed: 0,
      files_failed: 0,
    },
  });
  getImportBatch.mockResolvedValue({
    data: {
      id: 3,
      status: 'completed',
      files_total: 2,
      files_processed: 2,
      files_failed: 0,
    },
  });
  getImportItems.mockResolvedValue({
    data: [
      {
        id: 1,
        filename: 'interview.txt',
        status: 'processed',
        document_id: 10,
        error: '',
      },
    ],
  });

  render(<BatchImportForm onCompleted={onCompleted} />);

  const file = new File(['zip'], 'archive.zip', { type: 'application/zip' });
  await act(async () => {
    userEvent.upload(screen.getByLabelText('ZIP-архив с TXT/DOCX'), file);
  });
  await act(async () => {
    fireEvent.click(screen.getByRole('button', { name: 'Импортировать ZIP' }));
  });

  await waitFor(() => expect(createImportBatch).toHaveBeenCalledWith(file));
  expect(await screen.findByText('Архив поставлен в очередь.')).toBeInTheDocument();

  await act(async () => {
    jest.advanceTimersByTime(2500);
    await Promise.resolve();
  });

  expect(await screen.findByText('Обработано 2 из 2 файлов. Импорт завершен.'))
    .toBeInTheDocument();
  expect(await screen.findByText(/interview.txt/)).toBeInTheDocument();
  expect(onCompleted).toHaveBeenCalledTimes(1);
});

test('shows completed with errors import result', async () => {
  createImportBatch.mockResolvedValue({
    data: {
      id: 4,
      status: 'pending',
      files_total: 0,
      files_processed: 0,
      files_failed: 0,
    },
  });
  getImportBatch.mockResolvedValue({
    data: {
      id: 4,
      status: 'completed_with_errors',
      files_total: 2,
      files_processed: 1,
      files_failed: 1,
    },
  });
  getImportItems.mockResolvedValue({
    data: [
      {
        id: 2,
        filename: 'broken.docx',
        status: 'failed',
        document_id: null,
        error: 'Document is empty.',
      },
    ],
  });

  render(<BatchImportForm />);
  await act(async () => {
    userEvent.upload(
      screen.getByLabelText('ZIP-архив с TXT/DOCX'),
      new File(['zip'], 'archive.zip', { type: 'application/zip' })
    );
  });
  await act(async () => {
    fireEvent.click(screen.getByRole('button', { name: 'Импортировать ZIP' }));
  });

  await waitFor(() => expect(createImportBatch).toHaveBeenCalledTimes(1));
  await act(async () => {
    jest.advanceTimersByTime(2500);
    await Promise.resolve();
  });

  expect(await screen.findByText('Обработано 2 из 2 файлов. Импорт завершен с ошибками.'))
    .toBeInTheDocument();
  expect(await screen.findByText(/broken.docx - Document is empty./))
    .toBeInTheDocument();
});

test('shows failed import status and stops polling', async () => {
  createImportBatch.mockResolvedValue({
    data: {
      id: 5,
      status: 'pending',
      files_total: 0,
      files_processed: 0,
      files_failed: 0,
    },
  });
  getImportBatch.mockResolvedValue({
    data: {
      id: 5,
      status: 'failed',
      files_total: 0,
      files_processed: 0,
      files_failed: 0,
      error: 'Invalid ZIP archive.',
    },
  });

  render(<BatchImportForm />);
  await act(async () => {
    userEvent.upload(
      screen.getByLabelText('ZIP-архив с TXT/DOCX'),
      new File(['bad'], 'broken.zip', { type: 'application/zip' })
    );
  });
  await act(async () => {
    fireEvent.click(screen.getByRole('button', { name: 'Импортировать ZIP' }));
  });

  await waitFor(() => expect(createImportBatch).toHaveBeenCalledTimes(1));
  await act(async () => {
    jest.advanceTimersByTime(2500);
    await Promise.resolve();
  });

  expect(await screen.findByText('Invalid ZIP archive.')).toBeInTheDocument();

  await act(async () => {
    jest.advanceTimersByTime(5000);
    await Promise.resolve();
  });
  expect(getImportBatch).toHaveBeenCalledTimes(1);
});

test('rejects non-ZIP files before request', async () => {
  render(<BatchImportForm />);

  await act(async () => {
    userEvent.upload(
      screen.getByLabelText('ZIP-архив с TXT/DOCX'),
      new File(['txt'], 'note.txt', { type: 'text/plain' })
    );
  });
  await act(async () => {
    fireEvent.click(screen.getByRole('button', { name: 'Импортировать ZIP' }));
  });

  expect(screen.getByText('Поддерживаются только .zip архивы')).toBeInTheDocument();
  expect(createImportBatch).not.toHaveBeenCalled();
});

test('clears scheduled polling on unmount', async () => {
  createImportBatch.mockResolvedValue({
    data: {
      id: 6,
      status: 'pending',
      files_total: 0,
      files_processed: 0,
      files_failed: 0,
    },
  });

  const { unmount } = render(<BatchImportForm />);
  await act(async () => {
    userEvent.upload(
      screen.getByLabelText('ZIP-архив с TXT/DOCX'),
      new File(['zip'], 'archive.zip', { type: 'application/zip' })
    );
  });
  await act(async () => {
    fireEvent.click(screen.getByRole('button', { name: 'Импортировать ZIP' }));
  });

  await waitFor(() => expect(createImportBatch).toHaveBeenCalledTimes(1));
  unmount();

  await act(async () => {
    jest.advanceTimersByTime(2500);
    await Promise.resolve();
  });
  expect(getImportBatch).not.toHaveBeenCalled();
});
