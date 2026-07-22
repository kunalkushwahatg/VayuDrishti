"""City boundary resolution via OpenStreetMap / Nominatim.

Accuracy comes from *selecting the right feature*, not just the first polygon.
Nominatim returns clean, pre-assembled polygons; the problem was that the old
code grabbed the first polygon of ANY type — which could be a townhall building,
a mall, a park, or a whole district instead of the actual city outline.

This version:
  1. queries several name variants,
  2. keeps only real administrative boundaries (boundary/administrative),
  3. scores them by admin_level (prefers municipality level 8), exact-name match,
     and "Municipal Corporation" naming,
  4. falls back to a large non-building polygon, then a smooth circle.
"""
import json
import math
import time
import requests

NOMINATIM = "https://nominatim.openstreetmap.org/search"
HEADERS = {"User-Agent": "VayuDrishti/1.0 (air-quality-platform)"}
TIMEOUT = 20
# Score at/above which we stop querying more variants (a city-level admin
# boundary whose name matches exactly — no need to look further).
GOOD_ENOUGH = 240


def _polygon_span_km(feat):
    """Rough max dimension (km) of a polygon's bounding box — used to reject
    tiny building/POI polygons that aren't city areas."""
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


def _score(feat, query_name):
    """Higher = better city outline. Negative = reject (not an admin boundary)."""
    p = feat.get("properties", {})
    if not (p.get("category") == "boundary" and p.get("type") == "administrative"):
        return -1
    ex = p.get("extratags") or {}
    name = (p.get("display_name") or "")
    score = 100
    try:
        lvl = int(ex.get("admin_level"))
        # Municipality (8) is the ideal city outline; nearby levels are okay,
        # sub-city wards (>8) and broad districts/states (<6) are less ideal.
        score += {8: 100, 7: 80, 6: 60, 5: 35, 4: 15}.get(lvl, 25 if lvl > 8 else 10)
    except (TypeError, ValueError):
        pass
    if name.lower().startswith(query_name.lower()):
        score += 60  # exact city, not e.g. "Navi Mumbai" for "Mumbai"
    low = name.lower()
    if "municipal corporation" in low or "municipality" in low or "corporation" in low:
        score += 25
    return score


def _query(q):
    try:
        return requests.get(NOMINATIM, params={
            "q": q, "format": "geojson", "polygon_geojson": 1, "limit": 8,
            "extratags": 1, "countrycodes": "in",  # India only — avoids e.g. Delhi, Iowa
        }, headers=HEADERS, timeout=TIMEOUT).json()
    except Exception as e:
        print(f"Nominatim query failed ({q}): {e}")
        return {}


def _circle_feature(name, lat, lon, radius_km=6.0, sides=48):
    """A smooth many-sided circle — a far better fallback than a square box."""
    coords = []
    dlat = radius_km / 111.0
    dlon = radius_km / (111.0 * max(math.cos(math.radians(lat)), 0.01))
    for i in range(sides + 1):
        theta = 2 * math.pi * i / sides
        coords.append([lon + dlon * math.cos(theta), lat + dlat * math.sin(theta)])
    return {
        "type": "Feature",
        "properties": {"name": f"{name} (approximate area)", "approximate": True},
        "geometry": {"type": "Polygon", "coordinates": [coords]},
    }


def fetch_city_boundary(name, lat, lon):
    """Return a GeoJSON Feature (JSON string) for the city's real administrative
    outline. Prefers the Geoapify Boundaries API (if a key is set), then the OSM
    admin-boundary selection below, then a smooth circle."""
    # 1. Geoapify Boundaries API (high quality) — only if configured.
    from src.ingestion.boundaries_geoapify import has_geoapify_key, fetch_boundary_geoapify
    if has_geoapify_key():
        gj = fetch_boundary_geoapify(name, lat, lon)
        if gj:
            return gj

    # 2. OSM / Nominatim admin-boundary selection.
    variants = [f"{name}, India", f"{name} Municipal Corporation", f"Greater {name}", name]
    best_admin = (-1, None)     # (score, feature)
    best_area = (0.0, None)     # (span_km, feature) — non-admin fallback
    seen = set()

    for i, q in enumerate(variants):
        for feat in _query(q).get("features", []):
            if feat.get("geometry", {}).get("type") not in ("Polygon", "MultiPolygon"):
                continue
            key = feat.get("properties", {}).get("display_name", "")
            if key in seen:
                continue
            seen.add(key)

            s = _score(feat, name)
            if s >= 0:
                if s > best_admin[0]:
                    best_admin = (s, feat)
            else:
                # Non-admin polygon: keep the largest area-like one (>3km span),
                # so we never return a tiny building/POI footprint.
                span = _polygon_span_km(feat)
                if span >= 3.0 and span > best_area[0]:
                    best_area = (span, feat)

        if best_admin[0] >= GOOD_ENOUGH:
            break
        if i < len(variants) - 1:
            time.sleep(1)  # respect Nominatim usage policy

    if best_admin[1] is not None:
        lvl = (best_admin[1]["properties"].get("extratags") or {}).get("admin_level")
        print(f"Boundary for {name}: admin_level={lvl} (score {best_admin[0]})")
        return json.dumps(best_admin[1])
    if best_area[1] is not None:
        print(f"Boundary for {name}: no admin boundary; using area polygon (~{best_area[0]:.0f}km)")
        return json.dumps(best_area[1])
    print(f"Boundary for {name}: nothing suitable — circular approximation.")
    return json.dumps(_circle_feature(name, lat, lon))
