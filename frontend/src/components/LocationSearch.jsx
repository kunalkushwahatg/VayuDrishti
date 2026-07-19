import { useState } from 'react';

export default function LocationSearch({ onLocationSelect }) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  
  const searchNominatim = async (e) => {
    e.preventDefault();
    if (!query) return;
    
    setLoading(true);
    try {
      const res = await fetch(`https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(query)}&format=json&limit=5&countrycodes=in`);
      const data = await res.json();
      setResults(data);
    } catch (err) {
      console.error(err);
    }
    setLoading(false);
  };

  const handleSelect = async (place) => {
    setQuery(place.display_name);
    setResults([]);
    
    const lat = parseFloat(place.lat);
    const lon = parseFloat(place.lon);
    
    // Extract a shorter name for the city/ward
    const name = place.name || place.display_name.split(',')[0];
    
    onLocationSelect({ name, lat, lon });
  };

  return (
    <div style={{ position: 'relative', minWidth: '300px' }}>
      <form onSubmit={searchNominatim} style={{ display: 'flex', gap: '8px', zIndex: 100, position: 'relative' }}>
        <input 
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search any place in India (e.g. Mumbai)..."
          style={{
            flex: 1,
            padding: '8px 16px',
            borderRadius: '20px',
            border: '1px solid var(--border)',
            background: '#ffffff',
            color: 'var(--text-primary)',
            outline: 'none',
            fontSize: '0.9rem',
            boxShadow: 'inset 0 1px 3px rgba(0,0,0,0.05)'
          }}
        />
        <button 
          type="submit" 
          disabled={loading}
          style={{
            padding: '8px 18px',
            borderRadius: '20px',
            border: 'none',
            background: 'var(--accent)',
            color: 'white',
            cursor: loading ? 'wait' : 'pointer',
            fontWeight: 600,
            fontSize: '0.9rem',
            transition: 'background 0.2s'
          }}
          onMouseEnter={e => e.currentTarget.style.background = 'var(--accent-hover)'}
          onMouseLeave={e => e.currentTarget.style.background = 'var(--accent)'}
        >
          {loading ? '...' : 'Search'}
        </button>
      </form>
      
      {results.length > 0 && (
        <div style={{
          position: 'absolute',
          top: '100%',
          left: 0,
          right: 0,
          marginTop: '8px',
          background: 'var(--surface)',
          border: '1px solid var(--border)',
          borderRadius: '12px',
          overflow: 'hidden',
          zIndex: 1000,
          boxShadow: 'var(--shadow-md)',
          color: 'var(--text-primary)'
        }}>
          {results.map((r, i) => (
            <div 
              key={i}
              onClick={() => handleSelect(r)}
              style={{
                padding: '12px 16px',
                cursor: 'pointer',
                borderBottom: i < results.length - 1 ? '1px solid var(--border)' : 'none',
                transition: 'background 0.2s',
                fontSize: '0.9rem'
              }}
              onMouseOver={(e) => e.currentTarget.style.background = 'var(--surface-hover)'}
              onMouseOut={(e) => e.currentTarget.style.background = 'var(--surface)'}
            >
              {r.display_name}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
