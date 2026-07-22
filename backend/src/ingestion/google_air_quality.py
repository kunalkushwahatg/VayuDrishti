"""Google Maps Platform — Air Quality API client.

Optional, higher-fidelity data source. Enabled only when GOOGLE_MAPS_API_KEY is
set (a billing-enabled Google Cloud key). Provides:
  - pre-rendered heatmap tiles (global, no grid-building / rate-limit gaps)
  - current conditions (with India CPCB local AQI)
  - up to 96h hourly forecast
  - population-segmented health recommendations

Everything degrades gracefully to None/False when no key is configured, so the
rest of the app keeps working on the free Open-Meteo path.
"""
import os
import requests
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

load_dotenv()

BASE = "https://airquality.googleapis.com/v1"
# Heatmap tile index. UAQI works globally; IND_CPCB gives India CPCB colouring
# where available. Override via GOOGLE_AQ_MAPTYPE.
DEFAULT_MAP_TYPE = "UAQI_INDIGO_PERSIAN"
HTTP_TIMEOUT = 15


def get_key():
    return os.getenv("GOOGLE_MAPS_API_KEY")


def has_google_key():
    return bool(get_key())


def map_type():
    return os.getenv("GOOGLE_AQ_MAPTYPE", DEFAULT_MAP_TYPE)


def heatmap_tile_url(z, x, y):
    """Server-side Google heatmap tile URL (includes the key). The frontend never
    sees this — it goes through the backend tile proxy instead."""
    key = get_key()
    if not key:
        return None
    return f"{BASE}/mapTypes/{map_type()}/heatmapTiles/{z}/{x}/{y}?key={key}"


def fetch_tile(z, x, y):
    """Fetch a single heatmap tile as PNG bytes, or None on failure/no key."""
    url = heatmap_tile_url(z, x, y)
    if not url:
        return None
    try:
        r = requests.get(url, timeout=HTTP_TIMEOUT)
        if r.status_code == 200 and r.content:
            return r.content
        print(f"Google tile {z}/{x}/{y} -> HTTP {r.status_code}")
    except Exception as e:
        print(f"Google tile fetch failed: {e}")
    return None


def _india_local_aqi_body(lat, lon, extra=None):
    body = {
        "location": {"latitude": lat, "longitude": lon},
        "extraComputations": extra or [
            "HEALTH_RECOMMENDATIONS",
            "DOMINANT_POLLUTANT_CONCENTRATION",
            "POLLUTANT_CONCENTRATION",
            "LOCAL_AQI",
        ],
        # Ask for India's CPCB index in addition to the Universal AQI.
        "customLocalAqis": [{"regionCode": "in", "aqi": "ind_cpcb"}],
        "languageCode": "en",
    }
    return body


def fetch_current(lat, lon):
    """Current conditions incl. India CPCB AQI + health recommendations, or None."""
    key = get_key()
    if not key:
        return None
    try:
        r = requests.post(f"{BASE}/currentConditions:lookup?key={key}",
                          json=_india_local_aqi_body(lat, lon), timeout=HTTP_TIMEOUT)
        if r.status_code == 200:
            return r.json()
        print(f"Google currentConditions -> HTTP {r.status_code}: {r.text[:160]}")
    except Exception as e:
        print(f"Google currentConditions failed: {e}")
    return None


def fetch_forecast(lat, lon, hours=72):
    """Up to 96h hourly forecast for a point, or None. Returns Google's raw JSON
    (hourlyForecasts[]) so callers can adapt it to the local schema."""
    key = get_key()
    if not key:
        return None
    # forecast:lookup requires an explicit period; start at the next full hour.
    hours = min(hours, 96)
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    start = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    end = (now + timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        r = requests.post(f"{BASE}/forecast:lookup?key={key}", json={
            "location": {"latitude": lat, "longitude": lon},
            "period": {"startTime": start, "endTime": end},
            "extraComputations": ["DOMINANT_POLLUTANT_CONCENTRATION", "LOCAL_AQI"],
            "customLocalAqis": [{"regionCode": "in", "aqi": "ind_cpcb"}],
            "pageSize": hours,
        }, timeout=HTTP_TIMEOUT)
        if r.status_code == 200:
            return r.json()
        print(f"Google forecast -> HTTP {r.status_code}: {r.text[:160]}")
    except Exception as e:
        print(f"Google forecast failed: {e}")
    return None


_POLLUTANT_LABELS = {
    "pm25": "PM2.5", "pm10": "PM10", "no2": "NO2", "so2": "SO2",
    "co": "CO", "o3": "O3", "nox": "NOx",
}

def pollutant_label(code):
    if not code:
        return None
    return _POLLUTANT_LABELS.get(code.lower(), code.upper())


def extract_india_aqi(record):
    """Pull the India CPCB AQI + dominant pollutant from a Google indexes[] record.
    Falls back to the Universal AQI if the local index isn't present."""
    indexes = (record or {}).get("indexes", [])
    ind = next((i for i in indexes if i.get("code") == "ind_cpcb"), None)
    chosen = ind or (indexes[0] if indexes else None)
    if not chosen:
        return None, None
    return chosen.get("aqi"), chosen.get("dominantPollutant")
