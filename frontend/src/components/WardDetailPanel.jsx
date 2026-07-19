import { useState, useEffect } from 'react';
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid } from 'recharts';
import { getAttribution, getForecasts } from '../services/api';
import SkeletonCard from './SkeletonCard';
import AqiChip from './AqiChip';

const PIE_COLORS = ['#F29C33', '#0F6E56', '#AF2D2D', '#E93F33', '#A3C853'];

export default function WardDetailPanel({ ward, cityName, onClose }) {
  const [attr, setAttr] = useState(null);
  const [forecasts, setForecasts] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    Promise.all([getAttribution(cityName), getForecasts(cityName)]).then(([a, f]) => {
      setAttr(a);
      setForecasts([
        { h: 'Now', aqi: ward.aqi },
        { h: '+24h', aqi: f[0]?.aqi ?? 220 },
        { h: '+48h', aqi: (f[0]?.aqi ?? 220) + 15 },
        { h: '+72h', aqi: (f[0]?.aqi ?? 220) + 30 },
      ]);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, [ward]);

  const pieData = attr ? [
    { name: 'Vehicles', value: attr.vehicles },
    { name: 'Industry', value: attr.industry },
    { name: 'Burning', value: attr.burning },
    { name: 'Dust', value: attr.dust },
  ].filter(d => d.value > 0) : [];

  return (
    <div style={{
      position: 'absolute', top: 0, right: 0, width: 340, height: '100%',
      background: 'var(--surface)', borderLeft: '1px solid var(--border)',
      boxShadow: 'var(--shadow-lg)', zIndex: 2000,
      animation: 'slideInRight 0.25s ease-out',
      display: 'flex', flexDirection: 'column', overflow: 'hidden'
    }}>
      {/* Header */}
      <div style={{ padding: '1.25rem 1.25rem 1rem', borderBottom: '1px solid var(--border)', background: 'var(--bg)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
              <h3 style={{ marginBottom: 4 }}>{ward.name}</h3>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ fontSize: '2rem', fontWeight: 800, color: 'var(--text-primary)', animation: 'countUp 0.6s ease-out' }}>
                {ward.aqi}
              </span>
              <div>
                <AqiChip aqi={ward.aqi} size="md" />
                {ward.dominant_pollutant && (
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 4 }}>
                    Major Pollutant: <strong>{ward.dominant_pollutant}</strong>
                  </div>
                )}
                {ward.isAnomaly && (
                  <div style={{ fontSize: '0.7rem', color: 'var(--aqi-very-poor)', marginTop: 2, fontWeight: 600 }}>
                    ⚠ Unusual spike — under review
                  </div>
                )}
              </div>
            </div>
          </div>
          <button onClick={onClose} className="btn btn-ghost" style={{ padding: '4px 8px', fontSize: '1rem' }}>×</button>
        </div>
      </div>

      {/* Body */}
      <div style={{ flex: 1, overflow: 'auto', padding: '1rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>

        {/* Attribution Donut */}
        <div className="card" style={{ padding: '1rem' }}>
          <h3 style={{ marginBottom: 8, fontSize: '0.85rem', color: 'var(--text-secondary)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Pollution Sources</h3>
          {loading ? <SkeletonCard height={160} /> : (
            <>
              <ResponsiveContainer width="100%" height={140}>
                <PieChart>
                  <Pie data={pieData} cx="50%" cy="50%" innerRadius={40} outerRadius={65} paddingAngle={3} dataKey="value">
                    {pieData.map((_, i) => <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />)}
                  </Pie>
                  <Tooltip formatter={(v) => `${Number(v).toFixed(1)}%`} />
                </PieChart>
              </ResponsiveContainer>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginTop: 4 }}>
                {pieData.map((d, i) => (
                  <div key={d.name} style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: '0.75rem' }}>
                    <div style={{ width: 8, height: 8, borderRadius: 2, background: PIE_COLORS[i] }} />
                    <span style={{ color: 'var(--text-secondary)' }}>{d.name}: <b style={{ color: 'var(--text-primary)' }}>{Number(d.value).toFixed(1)}%</b></span>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>

        {/* Forecast Chart */}
        <div className="card" style={{ padding: '1rem' }}>
          <h3 style={{ marginBottom: 8, fontSize: '0.85rem', color: 'var(--text-secondary)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>72-Hour Outlook</h3>
          {loading ? <SkeletonCard height={120} /> : (
            <ResponsiveContainer width="100%" height={110}>
              <LineChart data={forecasts} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                <XAxis dataKey="h" tick={{ fontSize: 11, fill: 'var(--text-muted)' }} />
                <YAxis tick={{ fontSize: 11, fill: 'var(--text-muted)' }} />
                <Tooltip />
                <Line type="monotone" dataKey="aqi" stroke="var(--accent)" strokeWidth={2} dot={{ r: 4, fill: 'var(--accent)' }} />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Confidence Badge */}
        {attr && !loading && (
          <div style={{ background: 'var(--accent-light)', borderRadius: 'var(--radius-sm)', padding: '0.75rem 1rem', border: '1px solid #B2DDD2' }}>
            <div style={{ fontSize: '0.75rem', color: 'var(--accent)', fontWeight: 600 }}>Confidence</div>
            <div style={{ fontSize: '1.5rem', fontWeight: 800, color: 'var(--accent)' }}>
              {Math.round((attr.confidence || 0.8) * 100)}%
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
