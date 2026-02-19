import LabelPill from './LabelPill';

const getSnippet = (text, start, end) => {
  if (typeof text !== 'string') {
    return '';
  }
  const safeStart = Number(start);
  const safeEnd = Number(end);
  if (
    !Number.isInteger(safeStart) ||
    !Number.isInteger(safeEnd) ||
    safeStart < 0 ||
    safeEnd <= safeStart
  ) {
    return '';
  }
  if (safeStart >= text.length) {
    return '';
  }
  return text.slice(safeStart, Math.min(safeEnd, text.length));
};

function AnnotationList({ annotations, labelsById, chunkText, onDelete, deletingId }) {
  if (!annotations.length) {
    return <p className="empty-state">Аннотаций пока нет.</p>;
  }

  return (
    <ul className="annotation-list">
      {annotations.map((annotation, index) => {
        const label = labelsById[annotation.label];
        const snippet = getSnippet(chunkText, annotation.localStart, annotation.localEnd) || '—';

        return (
          <li key={annotation.id} className="annotation-item">
            <span className="annotation-index">{index + 1}.</span>
            <span className="annotation-text">"{snippet}"</span>
            <span className="annotation-arrow">→</span>
            <LabelPill label={label} />
            <button
              type="button"
              className="btn danger small"
              onClick={() => onDelete(annotation.id)}
              disabled={deletingId === annotation.id}
            >
              Удалить
            </button>
          </li>
        );
      })}
    </ul>
  );
}

export default AnnotationList;
