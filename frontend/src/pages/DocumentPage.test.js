import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import api, {
  createExportJob,
  downloadExportJob,
  getExportJob,
} from '../api/api';
import DocumentPage from './DocumentPage';

jest.mock('../api/api', () => ({
  get: jest.fn(),
  patch: jest.fn(),
  post: jest.fn(),
  delete: jest.fn(),
  createExportJob: jest.fn(),
  downloadExportJob: jest.fn(),
  getExportJob: jest.fn(),
}));

const renderDocumentPage = () => {
  window.history.pushState({}, '', '/documents/7');
  return render(
    <MemoryRouter initialEntries={['/documents/7']}>
      <Routes>
        <Route path="/documents/:id" element={<DocumentPage />} />
      </Routes>
    </MemoryRouter>
  );
};

const mockInitialRequests = () => {
  api.get.mockImplementation((url) => {
    if (url === 'documents/7/') {
      return Promise.resolve({
        data: {
          id: 7,
          title: 'Интервью',
          slug: 'interview',
          original_filename: 'interview.txt',
          content: 'Текст интервью',
          created_at: '2026-01-01T10:00:00Z',
        },
      });
    }
    if (url === 'labels/') {
      return Promise.resolve({ data: [] });
    }
    if (url === 'annotations/') {
      return Promise.resolve({ data: [] });
    }
    if (url === 'documents/7/chunks/') {
      return Promise.resolve({
        data: {
          document_id: 7,
          page: 1,
          page_size: 1,
          has_next: false,
          has_prev: false,
          total_chunks: 1,
          chunk: ['Текст интервью'],
          chunk_index: 0,
          chunk_start: 0,
          chunk_end: 14,
        },
      });
    }
    return Promise.reject(new Error(`Unexpected GET ${url}`));
  });
};

beforeEach(() => {
  jest.useFakeTimers();
  api.get.mockReset();
  api.patch.mockReset();
  api.post.mockReset();
  api.delete.mockReset();
  createExportJob.mockReset();
  downloadExportJob.mockReset();
  getExportJob.mockReset();
  global.URL.createObjectURL = jest.fn(() => 'blob:export');
  global.URL.revokeObjectURL = jest.fn();
  HTMLAnchorElement.prototype.click = jest.fn();
  mockInitialRequests();
});

afterEach(() => {
  jest.clearAllTimers();
  jest.useRealTimers();
});

test('starts background export, polls status and downloads completed file', async () => {
  createExportJob.mockResolvedValue({
    data: {
      id: 11,
      document_id: 7,
      format: 'json',
      status: 'pending',
      error: '',
    },
  });
  getExportJob.mockResolvedValue({
    data: {
      id: 11,
      document_id: 7,
      format: 'json',
      status: 'completed',
      error: '',
    },
  });
  downloadExportJob.mockResolvedValue({
    data: new Blob(['{"schema_version":2}'], {
      type: 'application/json',
    }),
    headers: {
      'content-disposition': 'attachment; filename="interview_export.json"',
    },
  });

  renderDocumentPage();
  expect(await screen.findByDisplayValue('Интервью')).toBeInTheDocument();

  await act(async () => {
    fireEvent.click(screen.getByRole('button', { name: 'Экспортировать' }));
  });

  await waitFor(() => expect(createExportJob).toHaveBeenCalledWith(7, 'json'));
  expect(await screen.findByText('Экспорт поставлен в очередь.')).toBeInTheDocument();

  await act(async () => {
    jest.advanceTimersByTime(2500);
    await Promise.resolve();
  });

  expect(await screen.findByText('Файл экспорта готов.')).toBeInTheDocument();
  await act(async () => {
    fireEvent.click(screen.getByRole('button', { name: 'Скачать JSON' }));
  });

  await waitFor(() => expect(downloadExportJob).toHaveBeenCalledWith(11));
  expect(global.URL.createObjectURL).toHaveBeenCalledTimes(1);
  expect(global.URL.revokeObjectURL).toHaveBeenCalledWith('blob:export');
});

test('shows failed export status and lets user retry', async () => {
  createExportJob.mockResolvedValueOnce({
    data: {
      id: 12,
      document_id: 7,
      format: 'json',
      status: 'pending',
      error: '',
    },
  });
  createExportJob.mockResolvedValueOnce({
    data: {
      id: 13,
      document_id: 7,
      format: 'json',
      status: 'pending',
      error: '',
    },
  });
  getExportJob.mockResolvedValue({
    data: {
      id: 12,
      document_id: 7,
      format: 'json',
      status: 'failed',
      error: 'Export failed.',
    },
  });

  renderDocumentPage();
  expect(await screen.findByDisplayValue('Интервью')).toBeInTheDocument();

  await act(async () => {
    fireEvent.click(screen.getByRole('button', { name: 'Экспортировать' }));
  });
  await waitFor(() => expect(createExportJob).toHaveBeenCalledTimes(1));
  expect(await screen.findByText('Экспорт поставлен в очередь.')).toBeInTheDocument();

  await act(async () => {
    jest.advanceTimersByTime(2500);
    await Promise.resolve();
  });

  expect(await screen.findByText('Export failed.')).toBeInTheDocument();
  await act(async () => {
    jest.advanceTimersByTime(5000);
    await Promise.resolve();
  });
  expect(getExportJob).toHaveBeenCalledTimes(1);

  await act(async () => {
    fireEvent.click(screen.getByRole('button', { name: 'Экспортировать' }));
  });
  await waitFor(() => expect(createExportJob).toHaveBeenCalledTimes(2));
});
