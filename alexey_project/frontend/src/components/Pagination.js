function Pagination({ hasNext, hasPrev, onNext, onPrev, indicator }) {
  return (
    <div className="pagination">
      <button type="button" className="btn ghost" onClick={onPrev} disabled={!hasPrev}>
        Назад
      </button>
      <span className="pagination-indicator">{indicator}</span>
      <button type="button" className="btn ghost" onClick={onNext} disabled={!hasNext}>
        Вперед
      </button>
    </div>
  );
}

export default Pagination;
