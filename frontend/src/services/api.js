const BASE = 'http://localhost:8000/api';
export const API_BASE = BASE;

export async function initializeLocation(name, lat, lon) {
  const r = await fetch(`${BASE}/locations`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, lat, lon }),
  });
  return r.json();
}

export async function getCurrentAqi(city = 'Delhi', lat, lon) {
  const coords = (lat != null && lon != null) ? `&lat=${lat}&lon=${lon}` : '';
  const r = await fetch(`${BASE}/current_aqi?city_name=${encodeURIComponent(city)}${coords}`);
  return r.json();
}

export async function getBoundary(city = 'Delhi') {
  const r = await fetch(`${BASE}/boundary?city_name=${city}`);
  return r.json();
}

export async function getForecasts(city = 'Delhi', lat, lon) {
  const coords = (lat != null && lon != null) ? `&lat=${lat}&lon=${lon}` : '';
  const r = await fetch(`${BASE}/forecasts?city_name=${encodeURIComponent(city)}${coords}`);
  return r.json();
}

export async function getAttribution(city = 'Delhi') {
  const r = await fetch(`${BASE}/attribution?city_name=${city}`);
  return r.json();
}

export async function getEnforcement(city = 'Delhi') {
  const r = await fetch(`${BASE}/enforcement?city_name=${city}`);
  return r.json();
}

export async function getAnomalies(city = 'Delhi') {
  const r = await fetch(`${BASE}/anomalies?city_name=${city}`);
  return r.json();
}

export async function getAdvisories(city = 'Delhi') {
  const r = await fetch(`${BASE}/advisories?city_name=${city}`);
  return r.json();
}

export async function getHeatmap() {
  const r = await fetch(`${BASE}/heatmap`);
  if (!r.ok) return { points: [] };
  return r.json();
}

export async function getHeatmapConfig() {
  try {
    const r = await fetch(`${BASE}/heatmap/config`);
    if (!r.ok) return { provider: 'grid' };
    return r.json();
  } catch {
    return { provider: 'grid' };
  }
}

export async function getForecastAccuracy(city = 'Delhi') {
  const r = await fetch(`${BASE}/forecast_accuracy?city_name=${city}`);
  if (!r.ok) return null;
  return r.json();
}

export async function askAgent7(question, city = 'Delhi') {
  const r = await fetch(`${BASE}/ask`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, city_name: city }),
  });
  return r.json();
}
