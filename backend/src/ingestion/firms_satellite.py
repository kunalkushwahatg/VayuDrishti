"""NASA FIRMS active-fire satellite ingestion.

Pulls real VIIRS/MODIS thermal anomaly (active fire) detections around a location
from NASA's Fire Information for Resource Management System (FIRMS).

Requires a free FIRMS MAP_KEY (register at
https://firms.modaps.eosdis.nasa.gov/api/area/). Set it in backend/.env as:
    FIRMS_MAP_KEY=your_key_here

If no key is configured or the API returns nothing, callers should fall back
gracefully so the pipeline never crashes.
"""
import os
import csv
import io
import math
import requests
from datetime import datetime

FIRMS_BASE = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"
# VIIRS S-NPP gives 375m resolution — good for urban/agri fire detection.
FIRMS_SOURCE = "VIIRS_SNPP_NRT"


def haversine_km(lat1, lon1, lat2, lon2):
    """Great-circle distance between two points in kilometres."""
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def bearing_compass(lat1, lon1, lat2, lon2):
    """Compass direction FROM point 1 TO point 2 (e.g. 'North-West')."""
    dlon = math.radians(lon2 - lon1)
    y = math.sin(dlon) * math.cos(math.radians(lat2))
    x = math.cos(math.radians(lat1)) * math.sin(math.radians(lat2)) - \
        math.sin(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.cos(dlon)
    deg = (math.degrees(math.atan2(y, x)) + 360) % 360
    dirs = ["North", "North-East", "East", "South-East",
            "South", "South-West", "West", "North-West"]
    return dirs[int((deg + 22.5) % 360 // 45)]


def deg_to_compass(deg):
    """Convert a wind-direction bearing in degrees to a compass label."""
    if deg is None:
        return "Unknown"
    dirs = ["North", "North-East", "East", "South-East",
            "South", "South-West", "West", "North-West"]
    return dirs[int((deg + 22.5) % 360 // 45)]


def fetch_firms_hotspots(lat, lon, radius_deg=1.0, day_range=1):
    """Query NASA FIRMS for active fires in a bounding box around (lat, lon).

    Returns a list of dicts sorted nearest-first, or [] if no key / no data.
    Each dict: {lat, lon, frp, acq_date, distance_km, direction}.
    """
    map_key = os.getenv("FIRMS_MAP_KEY")
    if not map_key:
        print("FIRMS_MAP_KEY not set — skipping real satellite fetch.")
        return []

    west, south = lon - radius_deg, lat - radius_deg
    east, north = lon + radius_deg, lat + radius_deg
    area = f"{west},{south},{east},{north}"
    url = f"{FIRMS_BASE}/{map_key}/{FIRMS_SOURCE}/{area}/{day_range}"

    try:
        res = requests.get(url, timeout=15)
        if res.status_code != 200 or "Invalid" in res.text[:200]:
            print(f"FIRMS API returned {res.status_code}: {res.text[:120]}")
            return []
        reader = csv.DictReader(io.StringIO(res.text))
        fires = []
        for row in reader:
            try:
                flat = float(row["latitude"])
                flon = float(row["longitude"])
            except (KeyError, ValueError):
                continue
            fires.append({
                "lat": flat,
                "lon": flon,
                "frp": float(row.get("frp", 0) or 0),
                "acq_date": row.get("acq_date", ""),
                "acq_time": row.get("acq_time", ""),
                "confidence": row.get("confidence", ""),
                "distance_km": round(haversine_km(lat, lon, flat, flon), 1),
                "direction": bearing_compass(lat, lon, flat, flon),
            })
        fires.sort(key=lambda f: f["distance_km"])
        print(f"FIRMS: found {len(fires)} active fire(s) near ({lat:.3f},{lon:.3f}).")
        return fires
    except Exception as e:
        print(f"FIRMS fetch failed: {e}")
        return []


def is_upwind(fire_direction, wind_from_deg):
    """A fire is 'upwind' if it lies in the direction the wind is blowing FROM.

    Meteorological wind_direction is the direction the wind comes FROM, so a fire
    in that same compass direction will have its smoke carried toward us.
    """
    if wind_from_deg is None:
        return None
    wind_from_label = deg_to_compass(wind_from_deg)
    return fire_direction == wind_from_label
