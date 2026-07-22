import { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { getCurrentAqi, getBoundary, getHeatmap, getHeatmapConfig, API_BASE } from '../services/api';

// True AQI color for a value (CPCB bands) — used for the value-accurate field.
const aqiColor = (a) =>
  a <= 50 ? '#4ADE80' : a <= 100 ? '#A3E635' : a <= 200 ? '#FACC15'
  : a <= 300 ? '#FB923C' : a <= 400 ? '#F87171' : '#DC5B5B';

export default function CityMap({ onWardSelect, selectedWard, mapCenter, cityName, focusMap }) {
  const mapRef = useRef(null);
  const mapInstance = useRef(null);
  const polygonRef = useRef(null);
  const heatLayerRef = useRef(null);
  const [currentAqi, setCurrentAqi] = useState(null);
  const [boundary, setBoundary] = useState(null);
  const [showHeat, setShowHeat] = useState(false);
  const [heatMeta, setHeatMeta] = useState(null);

  // Fetch AQI and Boundary whenever city changes
  useEffect(() => {
    let mounted = true;
    // Pass the searched coordinates so Google answers for the exact point.
    getCurrentAqi(cityName, mapCenter?.[0], mapCenter?.[1]).then(res => {
      if (mounted) setCurrentAqi(res);
    }).catch(console.error);

    getBoundary(cityName).then(res => {
      if (mounted) setBoundary(res.geojson);
    }).catch(console.error);
    return () => { mounted = false; };
  }, [cityName, mapCenter]);

  useEffect(() => {
    if (mapInstance.current && mapCenter && currentAqi) {
      mapInstance.current.setView(mapCenter, boundary ? 11 : 13);
      
      const aqi = currentAqi.aqi;
      const noData = currentAqi.no_data || aqi == null;
      const resolvedColor = noData ? '#9AA0A6'
        : aqi <= 50 ? '#55A84F' : aqi <= 100 ? '#A3C853' : aqi <= 200 ? '#E8C830' : aqi <= 300 ? '#F29C33' : aqi <= 400 ? '#E93F33' : '#AF2D2D';
      
      if (polygonRef.current) {
        mapInstance.current.removeLayer(polygonRef.current);
      }
      
      if (boundary) {
        polygonRef.current = L.geoJSON(boundary, {
          style: {
            color: resolvedColor,
            fillColor: resolvedColor,
            fillOpacity: 0.45,
            weight: 2
          }
        }).addTo(mapInstance.current);
      } else {
        // Fallback when no real boundary: draw a smooth circle, never a square.
        const [centerLat, centerLon] = mapCenter;
        const rLat = 0.045, rLon = 0.045 / Math.max(Math.cos(centerLat * Math.PI / 180), 0.01);
        const circle = [];
        for (let i = 0; i <= 48; i++) {
          const a = (2 * Math.PI * i) / 48;
          circle.push([centerLat + rLat * Math.sin(a), centerLon + rLon * Math.cos(a)]);
        }
        polygonRef.current = L.polygon(circle, {
          color: resolvedColor, fillColor: resolvedColor, fillOpacity: 0.35, weight: 2, dashArray: '5,5'
        }).addTo(mapInstance.current);
      }
      
      const tip = noData
        ? `<b>${cityName}</b><br>No live data available for this region`
        : `<b>${cityName}</b><br>${currentAqi.stale ? 'Last known' : 'Live'} AQI: ${aqi} (${currentAqi.dominant_pollutant})`
          + (currentAqi.stale && currentAqi.as_of ? `<br><i>as of ${new Date(currentAqi.as_of).toLocaleString('en-IN')}</i>` : '');
      polygonRef.current.bindTooltip(tip);

      polygonRef.current.on('click', () => onWardSelect({
        id: 1,
        name: cityName,
        aqi: aqi,
        dominant_pollutant: currentAqi.dominant_pollutant,
        noData: noData,
        stale: currentAqi.stale,
      }));
    }
  }, [mapCenter, cityName, currentAqi, boundary]);

  // India-wide AQI heat layer (pre-computed grid), toggled on/off.
  useEffect(() => {
    const map = mapInstance.current;
    if (!map) return;
    if (showHeat) {
      if (heatLayerRef.current) { map.removeLayer(heatLayerRef.current); heatLayerRef.current = null; }
      map.flyTo([22.5, 80.0], 5, { animate: true, duration: 1 });
      getHeatmapConfig().then(cfg => {
        if (heatLayerRef.current) { map.removeLayer(heatLayerRef.current); heatLayerRef.current = null; }
        if (cfg.provider === 'google') {
          // Pre-rendered Google Air Quality heatmap tiles (via backend proxy).
          heatLayerRef.current = L.tileLayer(`${API_BASE}/heatmap/tile/{z}/{x}/{y}`, {
            opacity: 0.65, maxZoom: 16, crossOrigin: true,
          }).addTo(map);
          setHeatMeta({ source: `Google Air Quality (${cfg.map_type})` });
        } else {
          // Fallback: value-accurate field of soft circles from our Open-Meteo grid.
          getHeatmap().then(data => {
            if (heatLayerRef.current) { map.removeLayer(heatLayerRef.current); heatLayerRef.current = null; }
            const renderer = L.canvas({ padding: 0.5 });
            const group = L.layerGroup();
            (data.points || []).forEach(([lat, lon, aqi]) => {
              L.circle([lat, lon], {
                renderer, radius: 34000, stroke: false,
                fillColor: aqiColor(aqi), fillOpacity: 0.5,
              }).addTo(group);
            });
            group.addTo(map);
            heatLayerRef.current = group;
            setHeatMeta({ source: `${data.count?.toLocaleString() || 0} grid points`, updated: data.updated_at });
          }).catch(console.error);
        }
      }).catch(console.error);
    } else if (heatLayerRef.current) {
      map.removeLayer(heatLayerRef.current);
      heatLayerRef.current = null;
      setHeatMeta(null);
      if (mapCenter) map.flyTo(mapCenter, boundary ? 11 : 12, { animate: true, duration: 0.8 });
    }
  }, [showHeat]);

  // Handle focusMap to pan to a specific point and drop a marker
  useEffect(() => {
    if (mapInstance.current && focusMap) {
      mapInstance.current.flyTo([focusMap.lat, focusMap.lon], focusMap.zoom || 16, { animate: true, duration: 1 });
      
      const marker = L.circleMarker([focusMap.lat, focusMap.lon], {
        radius: 8,
        fillColor: 'var(--accent)',
        color: '#fff',
        weight: 2,
        opacity: 1,
        fillOpacity: 0.8
      }).addTo(mapInstance.current);

      marker.bindPopup('<b>Enforcement Target</b>').openPopup();

      const timer = setTimeout(() => {
        if (mapInstance.current) {
          mapInstance.current.removeLayer(marker);
        }
      }, 5000);
      return () => clearTimeout(timer);
    }
  }, [focusMap]);

  useEffect(() => {
    if (mapInstance.current) return;
    mapInstance.current = L.map(mapRef.current, {
      center: mapCenter,
      zoom: 13,
      zoomControl: false,
    });

    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
      attribution: '© CartoDB',
    }).addTo(mapInstance.current);

    // Anomaly pulse via setInterval on opacity
    let opacity = 0.45;
    let dir = -1;
    setInterval(() => {
      if (polygonRef.current) {
        opacity += dir * 0.015;
        if (opacity <= 0.2) dir = 1;
        if (opacity >= 0.45) dir = -1;
        polygonRef.current.setStyle({ fillOpacity: opacity });
      }
    }, 50);

  }, []);


  return (
    <div style={{ position: 'relative', height: '100%', borderRadius: 'var(--radius-lg)', overflow: 'hidden' }}>
      <div ref={mapRef} style={{ height: '100%', width: '100%' }} />
      <div style={{ position: 'absolute', top: 24, left: 24, zIndex: 1000, background: 'var(--surface)', padding: '0.5rem 1rem', borderRadius: '20px', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', boxShadow: 'var(--shadow-sm)', border: '1px solid var(--border)' }}>
        {showHeat ? '🔥 India AQI Heatmap' : `🗺️ ${cityName} Map · Click to inspect`}
      </div>

      {/* Heatmap toggle */}
      <button
        onClick={() => setShowHeat(v => !v)}
        style={{
          position: 'absolute', top: 24, right: 24, zIndex: 1000,
          background: showHeat ? 'var(--accent)' : 'var(--surface)',
          color: showHeat ? '#fff' : 'var(--text-secondary)',
          border: '1px solid var(--border)', borderRadius: '20px',
          padding: '0.5rem 1rem', fontSize: '0.8rem', fontWeight: 600,
          cursor: 'pointer', boxShadow: 'var(--shadow-sm)', fontFamily: 'inherit',
        }}
      >
        {showHeat ? '✕ Exit Heatmap' : '🔥 India Heatmap'}
      </button>

      {showHeat && heatMeta && (
        <div style={{
          position: 'absolute', top: 68, right: 24, zIndex: 1000,
          background: 'var(--surface)', border: '1px solid var(--border)',
          borderRadius: 'var(--radius-sm)', padding: '6px 10px', fontSize: '0.68rem',
          color: 'var(--text-muted)', boxShadow: 'var(--shadow-sm)',
        }}>
          {heatMeta.source}
          {heatMeta.updated ? ` · updated ${new Date(heatMeta.updated).toLocaleString('en-IN')}` : ''}
        </div>
      )}
      <div style={{
        position: 'absolute', bottom: 12, left: 12, zIndex: 1000,
        background: 'var(--surface)', borderRadius: 'var(--radius-sm)',
        padding: '8px 12px', boxShadow: 'var(--shadow-sm)',
        border: '1px solid var(--border)', display: 'flex', flexDirection: 'column', gap: 4
      }}>
        {[['Good','#55A84F'], ['Satisfactory','#A3C853'], ['Moderate','#E8C830'], ['Poor','#F29C33'], ['Very Poor','#E93F33'], ['Severe','#AF2D2D']].map(([l, c]) => (
          <div key={l} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <div style={{ width: 10, height: 10, borderRadius: 2, background: c }} />
            <span style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>{l}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
