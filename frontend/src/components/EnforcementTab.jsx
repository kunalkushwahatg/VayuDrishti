import { useState, useEffect } from 'react';
import { getEnforcement } from '../services/api';
import SkeletonCard from './SkeletonCard';

export default function EnforcementTab({ cityName, onLocate }) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [actioned, setActioned] = useState({});

  useEffect(() => {
    setLoading(true);
    getEnforcement(cityName).then(data => { setItems(data); setLoading(false); }).catch(() => setLoading(false));
  }, [cityName]);

  const handleAction = (id) => {
    setActioned(prev => ({ ...prev, [id]: true }));
  };

  if (loading) return <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>{[1,2,3].map(i => <SkeletonCard key={i} height={100} />)}</div>;
  if (!items.length) return (
    <div className="card" style={{ textAlign: 'center', padding: '2rem' }}>
      <h3>No pending enforcement items</h3>
      <p>All sites have been actioned today.</p>
    </div>
  );

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2>Priority Worklist</h2>
        <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', background: 'var(--bg)', padding: '2px 8px', borderRadius: 99, border: '1px solid var(--border)' }}>
          {items.length} site{items.length > 1 ? 's' : ''} today
        </span>
      </div>
      {items.map((item, i) => (
        <div key={i} className="card" style={{ borderLeft: `3px solid ${actioned[i] ? 'var(--status-actioned)' : 'var(--status-pending)'}` }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12 }}>
            <div style={{ flex: 1 }}>
              <div style={{ display: 'flex', align: 'center', gap: 8, marginBottom: 4 }}>
                <span style={{ fontWeight: 700, fontSize: '0.95rem' }}>Site: {item.site_name}</span>
                <span style={{
                  fontSize: '0.7rem', padding: '2px 8px', borderRadius: 99, fontWeight: 600,
                  background: actioned[i] ? 'var(--accent-light)' : 'rgba(250,204,21,0.14)',
                  color: actioned[i] ? 'var(--accent)' : 'var(--status-pending)'
                }}>
                  {actioned[i] ? 'Actioned' : 'Pending'}
                </span>
              </div>
              {(item.lat !== 0 && item.lon !== 0) && (
                <div style={{ fontSize: '0.75rem', marginBottom: 8, display: 'flex', gap: 8 }}>
                  <button onClick={() => onLocate(item.lat, item.lon)} style={{ color: 'var(--accent)', background: 'none', border: 'none', padding: 0, cursor: 'pointer', textDecoration: 'underline' }}>
                    📍 Locate on Map
                  </button>
                  <a href={`https://www.google.com/maps/search/?api=1&query=${item.lat},${item.lon}`} target="_blank" rel="noopener noreferrer" style={{ color: 'var(--text-muted)' }}>(Google Maps)</a>
                </div>
              )}
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Priority Score:</span>
                <div style={{ flex: 1, height: 6, background: 'var(--bg)', borderRadius: 3, overflow: 'hidden' }}>
                  <div style={{ width: `${Math.min(item.score * 10, 100)}%`, height: '100%', background: 'var(--accent)', borderRadius: 3, transition: 'width 0.6s ease' }} />
                </div>
                <b style={{ fontSize: '0.8rem' }}>{item.score?.toFixed(1)}</b>
              </div>
              {item.justification && (
                <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                  {item.justification.slice(0, 150)}{item.justification.length > 150 ? '…' : ''}
                </p>
              )}
            </div>
            {!actioned[i] && (
              <button className="btn btn-primary" style={{ whiteSpace: 'nowrap', flexShrink: 0 }} onClick={() => handleAction(i)}>
                Mark Actioned
              </button>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
