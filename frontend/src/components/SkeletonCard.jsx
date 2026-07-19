export default function SkeletonCard({ lines = 3, height = 120 }) {
  return (
    <div className="card" style={{ height, display: 'flex', flexDirection: 'column', gap: '0.6rem', justifyContent: 'center' }}>
      {Array.from({ length: lines }).map((_, i) => (
        <div key={i} className="skeleton" style={{ height: 14, width: i === lines - 1 ? '60%' : '100%' }} />
      ))}
    </div>
  );
}
