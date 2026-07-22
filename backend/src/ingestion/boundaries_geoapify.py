"""Geoapify Boundaries API — high-quality administrative city outlines.

Optional, preferred boundary source. Enabled when GEOAPIFY_API_KEY is set
(free tier: 100k requests). Given a lat/lon, the "part-of" endpoint returns the
administrative areas containing that point (city, county, state, country) as
GeoJSON polygons; we pick the city-level one.

Degrades to None with no key / no match, so the OSM logic in boundaries.py runs.
"""
import os
import math
import json
import requests
from dotenv import load_dotenv

load_dotenv()

PART_OF = "https://api.geoapify.com/v1/boundaries/part-of"
TIMEOUT = 20
# Geometry detail level (higher tolerance = smaller payload). Override via env.
DEFAULT_GEOMETRY = "geometry_1000"

# result_type values, most-city-like first, that we accept as a city outline.
_CITY_TYPES = ["city", "municipality", "town", "district", "county", "state_district"]


def get_key():
    return os.getenv("GEOAPIFY_API_KEY")


def has_geoapify_key():
    return bool(get_key())


def _span_km(feat):
    coords = []
    g = feat.get("geometry", {})
    if g.get("type") == "Polygon":
        for ring in g.get("coordinates", []):
            coords.extend(ring)
    elif g.get("type") == "MultiPolygon":
        for poly in g.get("coordinates", []):
            for ring in poly:
                coords.extend(ring)
    if not coords:
        return 0.0
    lats = [c[1] for c in coords]
    lons = [c[0] for c in coords]
    dlat = (max(lats) - min(lats)) * 111.0
    dlon = (max(lons) - min(lons)) * 111.0 * math.cos(math.radians(sum(lats) / len(lats)))
    return max(dlat, dlon)


def _pick_city_feature(features, name):
    """Choose the best city-level polygon from the containing admin areas."""
    polys = [f for f in features
             if f.get("geometry", {}).get("type") in ("Polygon", "MultiPolygon")]
    if not polys:
        return None

    def rank(feat):
        p = feat.get("properties", {})
        rt = (p.get("result_type") or p.get("type") or "").lower()
        fname = (p.get("name") or p.get("city") or p.get("formatted") or "").lower()
        span = _span_km(feat)
        # Lower rank tuple = better. Prefer known city types (by their order),
        # then exact-name match, then the smallest sensible area (>=2km).
        type_rank = _CITY_TYPES.index(rt) if rt in _CITY_TYPES else len(_CITY_TYPES)
        name_rank = 0 if fname.startswith(name.lower()) else 1
        size_penalty = span if span >= 2.0 else 9999  # reject tiny building-ish
        return (type_rank, name_rank, size_penalty)

    best = min(polys, key=rank)
    # Guard against a degenerate pick (everything tiny).
    return best if _span_km(best) >= 2.0 else None


def fetch_boundary_geoapify(name, lat, lon):
    """Return a GeoJSON Feature (JSON string) for the city's boundary, or None."""
    key = get_key()
    if not key:
        return None
    geometry = os.getenv("GEOAPIFY_GEOMETRY", DEFAULT_GEOMETRY)
    try:
        r = requests.get(PART_OF, params={
            "lat": lat, "lon": lon, "geometry": geometry,
            "boundary": "administrative", "apiKey": key,
        }, timeout=TIMEOUT)
        if r.status_code != 200:
            print(f"Geoapify boundaries -> HTTP {r.status_code}: {r.text[:140]}")
            return None
        data = r.json()
    except Exception as e:
        print(f"Geoapify boundaries failed: {e}")
        return None

    feat = _pick_city_feature(data.get("features", []), name)
    if not feat:
        print(f"Geoapify: no suitable city polygon for {name}.")
        return None
    p = feat.get("properties", {})
    print(f"Geoapify boundary for {name}: {p.get('result_type', '?')} "
          f"'{p.get('name', name)}' (~{_span_km(feat):.0f}km)")
    # Normalize to a single Feature the frontend already knows how to render.
    return json.dumps({"type": "Feature", "properties": {
        "name": p.get("name", name), "source": "geoapify",
        "result_type": p.get("result_type"),
    }, "geometry": feat.get("geometry")})
