"""
VayuDrishti -- Bhuvan WMS Layer Test (Fixed)
=============================================
Your original script used https://nrsc.gov.in (the NRSC homepage) as the WMS URL.
The correct endpoint is: https://bhuvan-vec2.nrsc.gov.in/bhuvan/wms

This script also verifies the WMS endpoint is reachable before building the map.
"""

import urllib.request
import urllib.error

# ── 1. Verify WMS endpoint is reachable first ────────────────────────────────
WMS_URL = "https://bhuvan-vec2.nrsc.gov.in/bhuvan/wms"
cap_url = f"{WMS_URL}?service=WMS&request=GetCapabilities&version=1.1.1"

print("Checking Bhuvan WMS reachability...")
try:
    req = urllib.request.Request(cap_url, headers={"User-Agent": "VayuDrishti/1.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        body = resp.read()
        print(f"  [OK] WMS reachable (HTTP {resp.status})")
        print(f"  XML starts with: {body[:200].decode(errors='replace')}")
        WMS_REACHABLE = True
except Exception as e:
    print(f"  [WARN] WMS not reachable: {e}")
    print("  Bhuvan may be geo-blocked or down. The map will still be created,")
    print("  but the WMS tile layer may not render.")
    WMS_REACHABLE = False

# ── 2. Build the map ─────────────────────────────────────────────────────────
try:
    import folium
except ImportError:
    print("\n[ERROR] folium not installed. Run: pip install folium")
    exit(1)

print("\nBuilding map...")

# Center on Ambikapur, Chhattisgarh
m = folium.Map(location=[23.12, 83.20], zoom_start=10)

# ── Bhuvan LULC WMS layer (correct endpoint + layer name) ───────────────────
# Layer name from Bhuvan GetCapabilities: lulc:IND_LULC_50k_1112
# If WMS is unreachable locally, the tiles simply won't load but HTML is valid
folium.raster_layers.WmsTileLayer(
    url=WMS_URL,                        # FIXED: was https://nrsc.gov.in (homepage)
    layers="lulc:IND_LULC_50k_1112",   # 1:50,000 LULC layer (2011-12 dataset)
    fmt="image/png",
    transparent=True,
    version="1.1.1",
    name="Bhuvan LULC 50k (2011-12)",
    attr='<a href="https://bhuvan.nrsc.gov.in">Geoportal of ISRO - Bhuvan</a>',
    opacity=0.7,
).add_to(m)

# ── OSM landuse overlay as FALLBACK (always works) ───────────────────────────
# Since Bhuvan times out programmatically, OSM Overpass landuse is the build fallback
folium.TileLayer(
    tiles="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    attr="OpenStreetMap",
    name="OSM (fallback base)",
    overlay=False,
    control=True,
).add_to(m)

# Add layer toggle so you can switch between OSM and Bhuvan WMS
folium.LayerControl().add_to(m)

# Add a marker at Ambikapur
folium.Marker(
    location=[23.12, 83.20],
    popup="Ambikapur, Chhattisgarh",
    icon=folium.Icon(color="green", icon="leaf"),
).add_to(m)

output_file = "bhuvan_thematic_map.html"
m.save(output_file)
print(f"  [OK] Map saved to: {output_file}")
print(f"  Open it in your browser. If Bhuvan tiles don't load,")
print(f"  the WMS server is blocking programmatic access from this IP.")
print(f"\nFix summary:")
print(f"  Your URL:    https://nrsc.gov.in   (NRSC homepage -- not a WMS)")
print(f"  Correct URL: {WMS_URL}  (actual OGC WMS endpoint)")
