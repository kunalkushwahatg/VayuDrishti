import { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { getAqiColor } from './AqiChip';
import { getCurrentAqi, getBoundary } from '../services/api';

export default function CityMap({ onWardSelect, selectedWard, mapCenter, cityName, focusMap }) {
  const mapRef = useRef(null);
  const mapInstance = useRef(null);
  const polygonRef = useRef(null);
  const [currentAqi, setCurrentAqi] = useState(null);
  const [boundary, setBoundary] = useState(null);

  // Fetch AQI and Boundary whenever city changes
  useEffect(() => {
    let mounted = true;
    getCurrentAqi(cityName).then(res => {
      if (mounted) setCurrentAqi(res);
    }).catch(console.error);
    
    getBoundary(cityName).then(res => {
      if (mounted) setBoundary(res.geojson);
    }).catch(console.error);
    return () => { mounted = false; };
  }, [cityName]);

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
        const centerLat = mapCenter[0];
        const centerLon = mapCenter[1];
        const dynamicCoords = [
          [centerLat + 0.008, centerLon - 0.008],
          [centerLat + 0.008, centerLon + 0.008],
          [centerLat - 0.008, centerLon + 0.008],
          [centerLat - 0.008, centerLon - 0.008],
        ];
        polygonRef.current = L.polygon(dynamicCoords, {
          color: resolvedColor, fillColor: resolvedColor, fillOpacity: 0.45, weight: 2
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

    L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
      attribution: '© CartoDB',
    }).addTo(mapInstance.current);

    L.control.zoom({ position: 'bottomright' }).addTo(mapInstance.current);

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
        🗺️ {cityName} Map · Click to inspect
      </div>
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
