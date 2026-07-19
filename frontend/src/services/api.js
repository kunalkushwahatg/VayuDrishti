const BASE = 'http://localhost:8000/api';

export async function initializeLocation(name, lat, lon) {
  const r = await fetch(`${BASE}/locations`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, lat, lon }),
  });
  return r.json();
}

export async function getCurrentAqi(city = 'Delhi') {
  const r = await fetch(`${BASE}/current_aqi?city_name=${city}`);
  return r.json();
}

export async function getBoundary(city = 'Delhi') {
  const r = await fetch(`${BASE}/boundary?city_name=${city}`);
  return r.json();
}

export async function getForecasts(city = 'Delhi') {
  const r = await fetch(`${BASE}/forecasts?city_name=${city}`);
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

export async function askAgent7(question, city = 'Delhi') {
  const r = await fetch(`${BASE}/ask`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, city_name: city }),
  });
  return r.json();
}
