"""India-wide AQI heatmap grid builder.

Pre-computes AQI on a grid across India using Open-Meteo's batched
multi-coordinate air-quality API, and stores it for the map's heat layer.
Designed to be run periodically (cron) so the endpoint serves cached data
instantly instead of hitting the API on every page load.
"""
import time
import requests
from datetime import datetime

from src.db.session import SessionLocal
from src.db.models import HeatmapCell
from src.ingestion.aqi_calculator import calculate_indian_aqi

# India bounding box (approx). Step controls resolution.
LAT_MIN, LAT_MAX = 7.5, 37.5
LON_MIN, LON_MAX = 68.0, 97.5
# Open-Meteo's free tier caps ~5,000 locations/hour. A full-India grid must stay
# under that in one run, so 0.55° (~60 km) keeps us near ~3,000 points with room
# to spare while still giving a smooth blurred heatmap.
STEP = 0.55
BATCH = 100         # coordinates per Open-Meteo request
THROTTLE_S = 1.0    # pause between batches (stay under the per-minute cap)
AQ_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"


def generate_grid():
    """Return a list of (lat, lon) covering the India bounding box."""
    pts = []
    lat = LAT_MIN
    while lat <= LAT_MAX:
        lon = LON_MIN
        while lon <= LON_MAX:
            pts.append((round(lat, 3), round(lon, 3)))
            lon += STEP
        lat += STEP
    return pts


def _fetch_batch(coords, retries=3):
    """Fetch AQI for a batch of coords; return list of (lat, lon, aqi, dominant).
    Retries with exponential backoff on failure/rate-limit so we don't leave holes."""
    lats = ",".join(str(c[0]) for c in coords)
    lons = ",".join(str(c[1]) for c in coords)
    # `current=` returns a single value per location (far lighter than 24 hourly
    # values), which keeps us well under the free-tier request weighting.
    url = f"{AQ_URL}?latitude={lats}&longitude={lons}&current=pm2_5,pm10&timezone=GMT"
    out = []
    data = None
    for attempt in range(retries):
        try:
            resp = requests.get(url, timeout=40)
            if resp.status_code == 429:  # rate-limited: back off and retry
                wait = 5 * (attempt + 1)
                print(f"  rate-limited (429), backing off {wait}s...")
                time.sleep(wait)
                continue
            data = resp.json()
            break
        except Exception as e:
            print(f"  batch attempt {attempt + 1} failed: {e}")
            time.sleep(3 * (attempt + 1))
    if data is None:
        return out
    # A single-coordinate batch returns a dict, not a list — normalize.
    if isinstance(data, dict):
        data = [data]
    for loc in data:
        cur = loc.get("current", {})
        pm25 = cur.get("pm2_5")
        pm10 = cur.get("pm10")
        if pm25 is None and pm10 is None:
            continue
        aqi, dom = calculate_indian_aqi(pm25, pm10, None, None, None)
        out.append((loc.get("latitude"), loc.get("longitude"), int(aqi), dom))
    return out


def refresh_heatmap():
    """Rebuild the whole grid and replace the stored heatmap. Returns cell count."""
    grid = generate_grid()
    print(f"Heatmap: fetching {len(grid)} grid points in batches of {BATCH}...")
    results = []
    total_batches = (len(grid) + BATCH - 1) // BATCH
    for bi, i in enumerate(range(0, len(grid), BATCH)):
        batch = grid[i:i + BATCH]
        got = _fetch_batch(batch)
        results.extend(got)
        if bi % 10 == 0:
            print(f"  batch {bi + 1}/{total_batches} — {len(results)} cells so far")
        time.sleep(THROTTLE_S)
    if not results:
        print("Heatmap: no results, keeping previous grid.")
        return 0

    db = SessionLocal()
    now = datetime.utcnow()
    db.query(HeatmapCell).delete()
    db.bulk_save_objects([
        HeatmapCell(lat=lat, lon=lon, aqi=aqi, dominant=dom, updated_at=now)
        for (lat, lon, aqi, dom) in results if lat is not None
    ])
    db.commit()
    db.close()
    print(f"Heatmap: stored {len(results)} cells at {now.isoformat()}.")
    return len(results)


if __name__ == "__main__":
    refresh_heatmap()
