import { useState } from 'react';
import './index.css';
import CityMap from './components/CityMap';
import WardDetailPanel from './components/WardDetailPanel';
import EnforcementTab from './components/EnforcementTab';
import AnomalyFeed from './components/AnomalyFeed';
import AiChatPanel from './components/AiChatPanel';
import LocationSearch from './components/LocationSearch';
import { initializeLocation } from './services/api';

const TABS = [
  { id: 'enforcement', label: 'Inspections' },
  { id: 'anomalies', label: 'Pollution Spikes' },
];

export default function App() {
  const [globalCity, setGlobalCity] = useState({ name: 'Delhi', lat: 28.6139, lon: 77.2090 });
  const [selectedWard, setSelectedWard] = useState(null);
  const [activeTab, setActiveTab] = useState('enforcement');
  const [mapCenter, setMapCenter] = useState([28.6139, 77.2090]);
  const [focusMap, setFocusMap] = useState(null);
  const [loadingCity, setLoadingCity] = useState(false);
  // Right panel starts collapsed; the map/heatmap is the default full-width view.
  // Clicking the expand rail opens the panel with the Inspection (Enforcement) tab.
  const [panelCollapsed, setPanelCollapsed] = useState(true);

  const isAiOpen = activeTab === 'ask';

  const handleLocationSelect = async (loc) => {
    setLoadingCity(true);
    try {
      await initializeLocation(loc.name, loc.lat, loc.lon);
      setGlobalCity(loc);
      setMapCenter([loc.lat, loc.lon]);
      setSelectedWard(null);
    } catch (e) {
      console.error(e);
    }
    setLoadingCity(false);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', background: 'var(--bg)', overflow: 'hidden' }}>

      {/* ===== HEADER ===== */}
      <header style={{
        background: 'var(--surface)',
        borderBottom: '1px solid var(--border)',
        padding: '0.6rem 1.5rem',
        display: 'flex',
        alignItems: 'center',
        gap: '1rem',
        flexShrink: 0,
        zIndex: 9999,
      }}>
        {/* Logo */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <div style={{
            width: 32, height: 32, borderRadius: 8,
            background: 'linear-gradient(135deg, var(--accent) 0%, #17A384 100%)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: '1rem', flexShrink: 0,
          }}>🌬️</div>
          <div>
            <div style={{ fontWeight: 800, fontSize: '1rem', color: 'var(--text-primary)', letterSpacing: '-0.02em' }}>VayuDrishti</div>
            <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', marginTop: -2 }}>Urban Air Intelligence</div>
          </div>
        </div>

        {/* Spacer */}
        <div style={{ flex: 1 }} />
        
        {/* Location Search */}
        <LocationSearch onLocationSelect={handleLocationSelect} />
        
        <div style={{ flex: 1 }} />

        {/* Status */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          {loadingCity && (
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Initializing Agents...</div>
          )}
        </div>
      </header>

      {/* ===== MAIN BODY ===== */}
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden', position: 'relative' }}>

        {/* LEFT — Map */}
        <div style={{ flex: panelCollapsed ? '1 1 100%' : '0 0 55%', position: 'relative', padding: '1rem 0 1rem 1rem', transition: 'flex-basis 0.3s ease' }}>
          <CityMap onWardSelect={setSelectedWard} selectedWard={selectedWard} mapCenter={mapCenter} cityName={globalCity.name} focusMap={focusMap} />
          {selectedWard && !isAiOpen && (
            <WardDetailPanel ward={selectedWard} cityName={globalCity.name} onClose={() => setSelectedWard(null)} />
          )}
        </div>

        {/* RIGHT — Tabbed Panels (collapsible to the right) */}
        {!panelCollapsed && (
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', padding: '1rem', gap: '0.75rem', overflow: 'hidden', minWidth: 0 }}>

          {/* Header row: tabs / AI header + collapse button */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0 }}>
            {!isAiOpen ? (
              <div className="tab-group" style={{ flex: 1, minWidth: 0 }}>
                {TABS.map(t => (
                  <button key={t.id} className={`tab-btn ${activeTab === t.id ? 'active' : ''}`} onClick={() => setActiveTab(t.id)}>
                    {t.label}
                  </button>
                ))}
              </div>
            ) : (
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, flex: 1, minWidth: 0 }}>
                <button className="btn btn-ghost" style={{ padding: '4px 10px', fontSize: '0.8rem' }} onClick={() => setActiveTab('enforcement')}>← Back</button>
                <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-secondary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  VayuDrishti AI · Ask anything
                </span>
              </div>
            )}
            <button
              onClick={() => setPanelCollapsed(true)}
              title="Collapse panel"
              style={{
                flexShrink: 0, width: 30, height: 30, borderRadius: 8,
                border: '1px solid var(--border)', background: 'var(--surface)',
                color: 'var(--text-secondary)', cursor: 'pointer', fontSize: '0.95rem',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
              }}
            >»</button>
          </div>

          {/* Tab content */}
          <div style={{ flex: 1, overflow: isAiOpen ? 'hidden' : 'auto', display: 'flex', flexDirection: 'column' }}>
            {activeTab === 'enforcement' && <EnforcementTab cityName={globalCity.name} onLocate={(lat, lon) => setFocusMap({lat, lon, zoom: 16})} />}
            {activeTab === 'anomalies' && <AnomalyFeed cityName={globalCity.name} />}
            {activeTab === 'ask' && (
              <div style={{
                flex: 1, background: 'var(--surface)', borderRadius: 'var(--radius-md)',
                border: '1px solid var(--border)', overflow: 'hidden', display: 'flex', flexDirection: 'column'
              }}>
                <AiChatPanel cityName={globalCity.name} />
              </div>
            )}
          </div>
        </div>
        )}

        {/* Collapsed rail — click to expand the panel back out */}
        {panelCollapsed && (
          <button
            onClick={() => setPanelCollapsed(false)}
            title="Expand panel"
            style={{
              flexShrink: 0, alignSelf: 'stretch', width: 40, margin: '1rem 1rem 1rem 0',
              borderRadius: 'var(--radius-md)', border: '1px solid var(--border)',
              background: 'var(--surface)', color: 'var(--text-secondary)', cursor: 'pointer',
              display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 12,
              fontFamily: 'inherit', fontSize: '0.75rem', fontWeight: 600,
            }}
          >
            <span style={{ fontSize: '1rem' }}>«</span>
            <span style={{ writingMode: 'vertical-rl', transform: 'rotate(180deg)', letterSpacing: '0.08em' }}>
              {activeTab === 'anomalies' ? 'Pollution Spikes' : 'Inspections'}
            </span>
          </button>
        )}

        {/* ===== FLOATING ASK AI BUTTON ===== */}
        {!isAiOpen && (
          <button
            onClick={() => { setPanelCollapsed(false); setActiveTab('ask'); }}
            style={{
              position: 'absolute',
              bottom: 24,
              right: 24,
              zIndex: 500,
              background: 'var(--accent)',
              color: 'white',
              border: 'none',
              borderRadius: 50,
              height: 52,
              padding: '0 22px',
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              fontFamily: 'inherit',
              fontSize: '0.88rem',
              fontWeight: 600,
              cursor: 'pointer',
              boxShadow: '0 4px 20px rgba(15,110,86,0.4)',
              transition: 'all 0.2s ease',
            }}
            onMouseEnter={e => { e.currentTarget.style.background = 'var(--accent-hover)'; e.currentTarget.style.transform = 'translateY(-2px)'; e.currentTarget.style.boxShadow = '0 6px 24px rgba(15,110,86,0.5)'; }}
            onMouseLeave={e => { e.currentTarget.style.background = 'var(--accent)'; e.currentTarget.style.transform = 'translateY(0)'; e.currentTarget.style.boxShadow = '0 4px 20px rgba(15,110,86,0.4)'; }}
          >
            <span style={{ fontSize: '1.1rem' }}>🤖</span>
            Ask AI
          </button>
        )}
      </div>

      {/* ===== FOOTER ===== */}
      <footer style={{
        background: 'var(--surface)',
        borderTop: '1px solid var(--border)',
        padding: '0.35rem 1.5rem',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        fontSize: '0.7rem',
        color: 'var(--text-muted)',
        flexShrink: 0,
      }}>
        <span>Real-time Air Quality Intelligence · {globalCity.name}</span>
        <span>Data: Open-Meteo Air Quality · NASA FIRMS Satellite · OpenStreetMap · Weather Forecasts</span>
        <span>VayuDrishti v1.0</span>
      </footer>
    </div>
  );
}
