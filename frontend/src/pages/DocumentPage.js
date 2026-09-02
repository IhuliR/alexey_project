import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import AnnotationList from '../components/AnnotationList';
import ErrorMessage from '../components/ErrorMessage';
import Loader from '../components/Loader';
import api, {
  createExportJob,
  downloadExportJob,
  getExportJob,
} from '../api/api';
import { getApiErrorMessage } from '../utils/apiErrors';
import { getRangeTextOffsets, normalizeNewlines } from '../utils/text';

const PAGE_SIZE = 1;
const EXPORT_POLLING_INTERVAL = 2500;
const EXPORT_TERMINAL_STATUSES = new Set(['completed', 'failed']);

const getErrorMessage = (error) => {
  if (error?.response?.data) {
    return JSON.stringify(error.response.data);
  }
  return 'Network or server error';
};

const getContentDispositionFilename = (contentDisposition) => {
  if (!contentDisposition) {
    return '';
  }

  const encodedMatch = contentDisposition.match(/filename\*=UTF-8''([^;]+)/i);
  if (encodedMatch?.[1]) {
    return decodeURIComponent(encodedMatch[1].replace(/"/g, ''));
  }

  const plainMatch = contentDisposition.match(/filename="?([^"]+)"?/i);
  return plainMatch?.[1] || '';
};

const downloadBlob = (blob, filename) => {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename || 'document_export.json';
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
};

const getExportStatusText = (job) => {
  if (!job) {
    return '';
  }
  if (job.status === 'completed') {
    return 'Файл экспорта готов.';
  }
  if (job.status === 'failed') {
    return job.error || 'Не удалось сформировать файл экспорта.';
  }
  if (job.status === 'processing') {
    return 'Формируем файл...';
  }
  return 'Экспорт поставлен в очередь.';
};

const toRgba = (hex, alpha) => {
  if (typeof hex !== 'string') {
    return `rgba(255, 235, 59, ${alpha})`;
  }

  let value = hex.replace('#', '').trim();
  if (value.length === 3) {
    value = value
      .split('')
      .map((char) => char + char)
      .join('');
  }
  if (!/^[0-9a-fA-F]{6}$/.test(value)) {
    return `rgba(255, 235, 59, ${alpha})`;
  }

  const number = Number.parseInt(value, 16);
  const r = (number >> 16) & 255;
  const g = (number >> 8) & 255;
  const b = number & 255;

  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
};

const buildSegments = (text, annotations) => {
  if (!text) {
    return [];
  }

  const sorted = annotations
    .filter(
      (annotation) =>
        Number.isInteger(annotation.localStart) &&
        Number.isInteger(annotation.localEnd) &&
        annotation.localStart >= 0 &&
        annotation.localEnd > annotation.localStart &&
        annotation.localStart < text.length
    )
    .map((annotation) => ({
      ...annotation,
      localEnd: Math.min(annotation.localEnd, text.length),
    }))
    .sort((a, b) => {
      if (a.localStart === b.localStart) {
        return a.localEnd - b.localEnd;
      }
      return a.localStart - b.localStart;
    });

  const accepted = [];
  let cursor = 0;
  sorted.forEach((annotation) => {
    if (annotation.localStart < cursor) {
      return;
    }
    accepted.push(annotation);
    cursor = annotation.localEnd;
  });

  const segments = [];
  let position = 0;

  accepted.forEach((annotation) => {
    if (position < annotation.localStart) {
      segments.push({
        key: `plain-${position}-${annotation.localStart}`,
        text: text.slice(position, annotation.localStart),
      });
    }

    segments.push({
      key: `annotation-${annotation.id}`,
      text: text.slice(annotation.localStart, annotation.localEnd),
      annotation,
    });

    position = annotation.localEnd;
  });

  if (position < text.length) {
    segments.push({
      key: `plain-${position}-${text.length}`,
      text: text.slice(position),
    });
  }

  return segments;
};

function DocumentPage() {
  const { id } = useParams();
  const documentId = Number(id);
  const contentRef = useRef(null);

  const [documentData, setDocumentData] = useState(null);
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [labels, setLabels] = useState([]);
  const [annotations, setAnnotations] = useState([]);

  const [chunkPage, setChunkPage] = useState(1);
  const [chunkData, setChunkData] = useState(null);
  const [chunkText, setChunkText] = useState('');
  const [chunkStart, setChunkStart] = useState(0);
  const [chunkEnd, setChunkEnd] = useState(0);

  const [selection, setSelection] = useState(null);
  const [loading, setLoading] = useState(true);
  const [chunkLoading, setChunkLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [assigning, setAssigning] = useState(false);
  const [deletingId, setDeletingId] = useState(null);
  const [error, setError] = useState('');
  const [saveMessage, setSaveMessage] = useState('');
  const [markupMessage, setMarkupMessage] = useState('');
  const [markupError, setMarkupError] = useState('');
  const [exportJob, setExportJob] = useState(null);
  const [exporting, setExporting] = useState(false);
  const [downloadingExport, setDownloadingExport] = useState(false);
  const [exportError, setExportError] = useState('');

  const labelsById = useMemo(() => {
    return labels.reduce((acc, label) => {
      acc[label.id] = label;
      return acc;
    }, {});
  }, [labels]);

  const clearBrowserSelection = useCallback(() => {
    const browserSelection = window.getSelection();
    if (browserSelection) {
      browserSelection.removeAllRanges();
    }
  }, []);

  const applyChunkState = useCallback((data) => {
    let nextChunkText = '';
    if (Array.isArray(data?.chunk)) {
      nextChunkText = String(data.chunk[0] ?? '');
    } else if (typeof data?.chunk === 'string') {
      nextChunkText = data.chunk;
    }
    const nextChunkStart = Number.isInteger(data?.chunk_start)
      ? data.chunk_start
      : Number(data?.chunk_start) || 0;
    const nextChunkEndRaw = Number.isInteger(data?.chunk_end)
      ? data.chunk_end
      : Number(data?.chunk_end);
    const nextChunkEnd = Number.isFinite(nextChunkEndRaw)
      ? nextChunkEndRaw
      : nextChunkStart + nextChunkText.length;

    setChunkData(data || null);
    setChunkPage(Number.isInteger(data?.page) ? data.page : 1);
    setChunkText(nextChunkText);
    setChunkStart(nextChunkStart);
    setChunkEnd(nextChunkEnd);
    setSelection(null);
    setMarkupError('');
    clearBrowserSelection();
  }, [clearBrowserSelection]);

  const fetchChunk = async (page, withLoader = false) => {
    if (withLoader) {
      setChunkLoading(true);
    }

    try {
      const response = await api.get(`documents/${documentId}/chunks/`, {
        params: {
          page,
          page_size: PAGE_SIZE,
        },
      });
      const data = response.data || null;
      applyChunkState(data);
      return data;
    } finally {
      if (withLoader) {
        setChunkLoading(false);
      }
    }
  };

  const refreshAnnotations = async () => {
    const response = await api.get('annotations/');
    setAnnotations(Array.isArray(response.data) ? response.data : []);
  };

  const refreshDocument = async () => {
    const response = await api.get(`documents/${documentId}/`);
    const nextDocument = response.data || null;
    setDocumentData(nextDocument);
    setTitle(nextDocument?.title || '');
    setContent(nextDocument?.content || '');
    return nextDocument;
  };

  useEffect(() => {
    let cancelled = false;

    if (Number.isNaN(documentId)) {
      setError('Некорректный идентификатор документа');
      setLoading(false);
      return undefined;
    }

    const loadInitialData = async () => {
      setLoading(true);
      setError('');
      setSaveMessage('');
      setMarkupMessage('');
      setMarkupError('');

      try {
        const [documentResponse, labelsResponse, annotationsResponse, chunkResponse] = await Promise.all([
          api.get(`documents/${documentId}/`),
          api.get('labels/'),
          api.get('annotations/'),
          api.get(`documents/${documentId}/chunks/`, {
            params: {
              page: 1,
              page_size: PAGE_SIZE,
            },
          }),
        ]);

        if (cancelled) {
          return;
        }

        const nextDocument = documentResponse.data || null;
        setDocumentData(nextDocument);
        setTitle(nextDocument?.title || '');
        setContent(nextDocument?.content || '');
        setLabels(Array.isArray(labelsResponse.data) ? labelsResponse.data : []);
        setAnnotations(Array.isArray(annotationsResponse.data) ? annotationsResponse.data : []);
        applyChunkState(chunkResponse.data || null);
      } catch (requestError) {
        if (!cancelled) {
          setError(getErrorMessage(requestError));
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    loadInitialData();

    return () => {
      cancelled = true;
    };
  }, [documentId, applyChunkState]);

  useEffect(() => {
    if (
      !exportJob?.id ||
      EXPORT_TERMINAL_STATUSES.has(exportJob.status)
    ) {
      return undefined;
    }

    let cancelled = false;
    const timeoutId = window.setTimeout(async () => {
      try {
        const response = await getExportJob(exportJob.id);
        if (!cancelled) {
          setExportJob(response.data || null);
          setExportError('');
        }
      } catch (requestError) {
        if (!cancelled) {
          setExportError(getApiErrorMessage(
            requestError,
            'Не удалось получить статус экспорта.'
          ));
        }
      }
    }, EXPORT_POLLING_INTERVAL);

    return () => {
      cancelled = true;
      window.clearTimeout(timeoutId);
    };
  }, [exportJob]);

  const documentAnnotations = useMemo(() => {
    return annotations.filter((annotation) => Number(annotation.document) === documentId);
  }, [annotations, documentId]);

  const chunkAnnotations = useMemo(() => {
    return documentAnnotations
      .map((annotation) => {
        const absoluteStart = Number(annotation.start);
        const absoluteEnd = Number(annotation.end);

        if (!Number.isInteger(absoluteStart) || !Number.isInteger(absoluteEnd)) {
          return null;
        }

        if (absoluteStart >= chunkEnd || absoluteEnd <= chunkStart) {
          return null;
        }

        const localStart = Math.max(absoluteStart, chunkStart) - chunkStart;
        const localEnd = Math.min(absoluteEnd, chunkEnd) - chunkStart;

        if (localEnd <= localStart || localStart < 0) {
          return null;
        }

        return {
          ...annotation,
          absoluteStart,
          absoluteEnd,
          localStart,
          localEnd,
        };
      })
      .filter(Boolean)
      .sort((a, b) => {
        if (a.localStart === b.localStart) {
          return a.localEnd - b.localEnd;
        }
        return a.localStart - b.localStart;
      });
  }, [documentAnnotations, chunkStart, chunkEnd]);

  const highlightedSegments = useMemo(() => {
    return buildSegments(chunkText, chunkAnnotations);
  }, [chunkText, chunkAnnotations]);

  const handleSelectionChange = () => {
    setMarkupMessage('');
    setMarkupError('');
    const container = contentRef.current;
    const currentSelection = window.getSelection();

    if (!container || !currentSelection || currentSelection.rangeCount === 0) {
      setSelection(null);
      return;
    }

    if (currentSelection.isCollapsed) {
      setSelection(null);
      return;
    }

    const range = currentSelection.getRangeAt(0);
    if (
      !container.contains(range.startContainer) ||
      !container.contains(range.endContainer)
    ) {
      setSelection(null);
      setMarkupError('Выделение должно находиться внутри текста документа');
      return;
    }

    let offsets;
    try {
      offsets = getRangeTextOffsets(container, range);
    } catch {
      setSelection(null);
      setMarkupError('Не удалось определить границы выделения');
      return;
    }

    const localStart = offsets.start;
    const localEnd = offsets.end;
    if (
      !Number.isInteger(localStart) ||
      !Number.isInteger(localEnd) ||
      localStart < 0 ||
      localEnd <= localStart ||
      localEnd > chunkText.length
    ) {
      setSelection(null);
      setMarkupError('Не удалось определить корректные границы выделения');
      return;
    }

    const absoluteStart = chunkStart + localStart;
    const absoluteEnd = chunkStart + localEnd;
    const sourceContent = documentData?.content || '';
    if (absoluteStart < 0 || absoluteEnd > sourceContent.length) {
      setSelection(null);
      setMarkupError('Выделение выходит за границы текста документа');
      return;
    }

    const selectedText = sourceContent.slice(absoluteStart, absoluteEnd);
    if (selectedText !== chunkText.slice(localStart, localEnd)) {
      setSelection(null);
      setMarkupError('Текст документа изменился. Обновите страницу');
      return;
    }

    if (!selectedText.trim()) {
      setSelection(null);
      setMarkupError('Нельзя разметить пустой фрагмент или только пробелы');
      return;
    }

    setSelection({
      start: absoluteStart,
      end: absoluteEnd,
      text: selectedText,
    });
  };

  const handlePrevChunk = async () => {
    if (!chunkData?.has_prev || chunkLoading) {
      return;
    }

    setError('');
    try {
      await fetchChunk(chunkPage - 1, true);
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    }
  };

  const handleNextChunk = async () => {
    if (!chunkData?.has_next || chunkLoading) {
      return;
    }

    setError('');
    try {
      await fetchChunk(chunkPage + 1, true);
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    }
  };

  const handleSaveDocument = async () => {
    setSaving(true);
    setError('');
    setSaveMessage('');

    try {
      const formData = new FormData();
      formData.append('title', title);
      formData.append('content', normalizeNewlines(content));

      const response = await api.patch(`documents/${documentId}/`, formData);
      if (response.data) {
        await refreshDocument();
        await fetchChunk(1, true);
        setSaveMessage('Документ сохранен');
      }
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setSaving(false);
    }
  };

  const handleAssignLabel = async (labelId) => {
    if (!selection || selection.start >= selection.end) {
      setMarkupError('Сначала выделите фрагмент текста');
      return;
    }

    setAssigning(true);
    setError('');
    setMarkupMessage('');
    setMarkupError('');

    try {
      const response = await api.post('annotations/', {
        document: documentId,
        label: labelId,
        start: selection.start,
        end: selection.end,
        text: selection.text,
      });

      if (response.data) {
        await refreshAnnotations();
        setSelection(null);
        clearBrowserSelection();
      }
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setAssigning(false);
    }
  };

  const handleDeleteAnnotation = async (annotationId) => {
    setDeletingId(annotationId);
    setError('');

    try {
      await api.delete(`annotations/${annotationId}/`);
      await refreshAnnotations();
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setDeletingId(null);
    }
  };

  const handleExport = async () => {
    setExporting(true);
    setExportError('');
    setExportJob(null);

    try {
      const response = await createExportJob(documentId, 'json');
      setExportJob(response.data || null);
    } catch (requestError) {
      setExportError(getApiErrorMessage(requestError, 'Не удалось запустить экспорт.'));
    } finally {
      setExporting(false);
    }
  };

  const handleDownloadExport = async () => {
    if (!exportJob?.id || exportJob.status !== 'completed') {
      return;
    }

    setDownloadingExport(true);
    setExportError('');

    try {
      const response = await downloadExportJob(exportJob.id);
      const filename = getContentDispositionFilename(
        response.headers?.['content-disposition']
      );
      downloadBlob(response.data, filename);
    } catch (requestError) {
      setExportError(getApiErrorMessage(requestError, 'Не удалось скачать экспорт.'));
    } finally {
      setDownloadingExport(false);
    }
  };

  const exportInProgress = exporting || (
    !exportError &&
    (
      exportJob?.status === 'pending' ||
      exportJob?.status === 'processing'
    )
  );

  const fragmentIndex = Number.isInteger(chunkData?.chunk_index) ? chunkData.chunk_index + 1 : chunkPage;
  const totalChunks = Number.isInteger(chunkData?.total_chunks) ? chunkData.total_chunks : 1;

  return (
    <div className="page">
      <main className="container">
        {loading ? (
          <Loader />
        ) : (
          <section className="card document-page">
            <Link to="/documents" className="back-link">
              ← Назад к списку документов
            </Link>

            <label className="field">
              <span className="visually-hidden">Название документа</span>
              <input
                type="text"
                value={title}
                onChange={(event) => setTitle(event.target.value)}
                className="document-title-input"
                placeholder="Название документа"
              />
            </label>

            <p className="document-date">
              Загружен:{' '}
              {documentData?.created_at
                ? new Date(documentData.created_at).toLocaleDateString('ru-RU')
                : '—'}
            </p>

            <div className="chunk-controls">
              <p className="chunk-indicator">
                Фрагмент {fragmentIndex} из {totalChunks}
              </p>
              <div className="chunk-nav-buttons">
                <button
                  type="button"
                  className="btn ghost"
                  onClick={handlePrevChunk}
                  disabled={!chunkData?.has_prev || chunkLoading}
                >
                  Назад
                </button>
                <button
                  type="button"
                  className="btn ghost"
                  onClick={handleNextChunk}
                  disabled={!chunkData?.has_next || chunkLoading}
                >
                  Вперед
                </button>
              </div>
            </div>

            <div
              className="document-content-box"
              ref={contentRef}
              onMouseUp={handleSelectionChange}
              onKeyUp={handleSelectionChange}
            >
              {highlightedSegments.map((segment) => {
                if (!segment.annotation) {
                  return <span key={segment.key}>{segment.text}</span>;
                }

                const label = labelsById[segment.annotation.label];
                return (
                  <span
                    key={segment.key}
                    className="highlighted-text"
                    style={{ backgroundColor: toRgba(label?.color, 0.35) }}
                  >
                    {segment.text}
                  </span>
                );
              })}
            </div>

            <div className="section">
              <p className="section-title">Выделите текст и выберите метку:</p>
              <div className="labels-row">
                {labels.map((label) => (
                  <button
                    key={label.id}
                    type="button"
                    className="btn ghost"
                    onClick={() => handleAssignLabel(label.id)}
                    disabled={assigning}
                  >
                    {label.name}
                  </button>
                ))}
              </div>
              {selection ? (
                <p className="selection-meta">
                  Абсолютное выделение: {selection.start}-{selection.end}
                </p>
              ) : null}
              <ErrorMessage message={markupError} />
            </div>

            <div className="section">
              <p className="section-title">Текущие аннотации:</p>
              <AnnotationList
                annotations={chunkAnnotations}
                labelsById={labelsById}
                chunkText={chunkText}
                onDelete={handleDeleteAnnotation}
                deletingId={deletingId}
              />
            </div>

            <div className="section">
              <label className="field">
                <span>Редактирование содержимого</span>
                <textarea
                  value={content}
                  rows={8}
                  onChange={(event) => setContent(event.target.value)}
                />
              </label>
              <div className="actions-row">
                <button type="button" className="btn" onClick={handleSaveDocument} disabled={saving}>
                  Сохранить документ
                </button>
              </div>
            </div>

            <div className="actions-split">
              <button
                type="button"
                className="btn secondary"
                onClick={() => setMarkupMessage('Разметка сохранена')}
              >
                Сохранить разметку
              </button>
              <button
                type="button"
                className="btn ghost"
                onClick={handleExport}
                disabled={exportInProgress}
              >
                {exportInProgress ? 'Формируем...' : 'Экспортировать'}
              </button>
            </div>

            {exportJob ? (
              <div className="job-status">
                <p>{getExportStatusText(exportJob)}</p>
                {exportJob.status === 'completed' ? (
                  <button
                    type="button"
                    className="btn secondary small"
                    onClick={handleDownloadExport}
                    disabled={downloadingExport}
                  >
                    {downloadingExport ? 'Скачивание...' : 'Скачать JSON'}
                  </button>
                ) : null}
              </div>
            ) : null}
            <ErrorMessage message={exportError} />
            {saveMessage ? <p className="success-message">{saveMessage}</p> : null}
            {markupMessage ? <p className="success-message">{markupMessage}</p> : null}
            <ErrorMessage message={error} />
          </section>
        )}
      </main>
    </div>
  );
}

export default DocumentPage;
