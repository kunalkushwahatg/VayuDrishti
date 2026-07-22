import { useState, useEffect } from 'react';
import { getAdvisories } from '../services/api';
import SkeletonCard from './SkeletonCard';

const CHANNEL_ICONS = { push: '📱', ivr: '📞', display: '🖥️' };
const CHANNEL_LABELS = { push: 'SMS / App Push', ivr: 'IVR Voice Script', display: 'Billboard Display' };
const CHANNEL_COLORS = { push: 'rgba(59,130,246,0.10)', ivr: 'rgba(139,92,246,0.10)', display: 'rgba(34,197,94,0.10)' };
const CHANNEL_ACCENT = { push: '#60A5FA', ivr: '#A78BFA', display: '#4ADE80' };

export default function AdvisoryView({ cityName }) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    getAdvisories(cityName).then(data => { setItems(data); setLoading(false); }).catch(() => setLoading(false));
  }, [cityName]);

  if (loading) return <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: 12 }}>{[1,2,3].map(i => <SkeletonCard key={i} height={160} />)}</div>;

  return (
    <div>
      <div style={{ marginBottom: '1rem' }}>
        <h2>Citizen Advisories</h2>
        <p style={{ fontSize: '0.85rem', marginTop: 4 }}>Auto-generated and localized based on the latest 24-hour air quality forecast.</p>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: 12 }}>
        {items.map((item, i) => (
          <div key={i} className="card" style={{ background: CHANNEL_COLORS[item.channel] || 'var(--surface)', border: `1px solid ${CHANNEL_ACCENT[item.channel]}30` }}>
            <div style={{ display: 'flex', align: 'center', gap: 8, marginBottom: 10 }}>
              <span style={{ fontSize: '1.4rem' }}>{CHANNEL_ICONS[item.channel] || '📢'}</span>
              <div>
                <div style={{ fontWeight: 700, fontSize: '0.85rem', color: CHANNEL_ACCENT[item.channel] }}>
                  {CHANNEL_LABELS[item.channel] || item.channel}
                </div>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>{item.language}</div>
              </div>
            </div>
            <div style={{ fontSize: '0.85rem', lineHeight: 1.6, color: 'var(--text-primary)' }}>
              {item.text}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
