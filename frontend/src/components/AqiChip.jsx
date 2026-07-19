export function getAqiColor(aqi) {
  if (aqi <= 50) return 'var(--aqi-good)';
  if (aqi <= 100) return 'var(--aqi-satisfactory)';
  if (aqi <= 200) return 'var(--aqi-moderate)';
  if (aqi <= 300) return 'var(--aqi-poor)';
  if (aqi <= 400) return 'var(--aqi-very-poor)';
  return 'var(--aqi-severe)';
}

export function getAqiLabel(aqi) {
  if (aqi <= 50) return 'Good';
  if (aqi <= 100) return 'Satisfactory';
  if (aqi <= 200) return 'Moderate';
  if (aqi <= 300) return 'Poor';
  if (aqi <= 400) return 'Very Poor';
  return 'Severe';
}

export default function AqiChip({ aqi, size = 'md' }) {
  const color = getAqiColor(aqi);
  const label = getAqiLabel(aqi);
  const sizes = { sm: { fontSize: '0.7rem', padding: '2px 8px' }, md: { fontSize: '0.8rem', padding: '4px 12px' }, lg: { fontSize: '1rem', padding: '6px 16px' } };
  return (
    <span style={{
      display: 'inline-block',
      background: color,
      color: 'white',
      borderRadius: 999,
      fontWeight: 600,
      letterSpacing: '0.02em',
      ...sizes[size]
    }}>
      {label}
    </span>
  );
}
