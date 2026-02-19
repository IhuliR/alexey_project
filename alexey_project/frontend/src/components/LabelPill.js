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

function LabelPill({ label }) {
  if (!label) {
    return <span className="label-pill">Без метки</span>;
  }

  return (
    <span
      className="label-pill"
      style={{
        backgroundColor: toRgba(label.color, 0.35),
        borderColor: toRgba(label.color, 0.7),
      }}
    >
      {label.name}
    </span>
  );
}

export default LabelPill;
