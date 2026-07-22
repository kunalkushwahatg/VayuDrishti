import { useState, useEffect } from 'react';
import { getAnomalies } from '../services/api';
import SkeletonCard from './SkeletonCard';

export default function AnomalyFeed({ cityName }) {
  const [anomalies, setAnomalies] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    getAnomalies(cityName).then(data => { setAnomalies(data); setLoading(false); }).catch(() => setLoading(false));
  }, [cityName]);

  if (loading) return <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>{[1,2].map(i => <SkeletonCard key={i} height={140} />)}</div>;
  if (!anomalies.length) return (
    <div className="card" style={{ textAlign: 'center', padding: '2rem' }}>
      <h3>All clear</h3>
      <p>No unusual pollution spikes detected in the last 24 hours.</p>
    </div>
  );

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <h2>Unusual Pollution Spikes</h2>
      {anomalies.map((item, i) => (
        <div key={i} className="card" style={{ borderLeft: '3px solid var(--aqi-very-poor)' }}>
          <div style={{ display: 'flex', justify: 'space-between', align: 'center', gap: 8, marginBottom: 8 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ fontSize: '1.5rem' }}>⚡</span>
              <div>
                <div style={{ fontWeight: 700 }}>AQI Spike Detected</div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  {new Date(item.timestamp).toLocaleString('en-IN')}
                </div>
              </div>
            </div>
            <div style={{ textAlign: 'right' }}>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Severity</div>
              <div style={{ fontWeight: 800, fontSize: '1.1rem', color: 'var(--aqi-very-poor)' }}>{item.z_score >= 3 ? 'High' : item.z_score >= 2 ? 'Medium' : 'Low'}</div>
            </div>
          </div>
          <div style={{ background: 'var(--bg)', borderRadius: 'var(--radius-sm)', padding: '0.75rem', fontSize: '0.82rem', color: 'var(--text-secondary)', lineHeight: 1.6 }}>
            {item.report}
          </div>
        </div>
      ))}
    </div>
  );
}
