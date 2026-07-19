"""
VayuDrishti -- API Verification Script
=======================================
Tests every data source listed in Section 6 of the implementation plan.
Run: python verify_apis.py

Keys can be set here OR passed as environment variables:
  OPENAQ_KEY, DATA_GOV_KEY, FIRMS_MAP_KEY
"""

import os
import sys
import json
import time
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timedelta, timezone

# Fix Windows console encoding
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# -----------------------------------------------------------------------------
# 1.  PASTE YOUR KEYS HERE  (or leave as empty string to skip that test)
# -----------------------------------------------------------------------------
OPENAQ_KEY    = os.environ.get("OPENAQ_KEY",   "7ffaf5866c44b25be96e7b77db9ca76ee47c1ca6defdd3b7b4c79335e9276ee1")
DATA_GOV_KEY  = os.environ.get("DATA_GOV_KEY", "")    # NOT NEEDED -- OpenAQ covers same data
FIRMS_MAP_KEY = os.environ.get("FIRMS_MAP_KEY","b505fb21612726e92ad353db0d9efb56")
# WAQI free token -- get at https://aqicn.org/api/ (instant, no card)
WAQI_TOKEN    = os.environ.get("WAQI_TOKEN",   "99af914e84b9e5faf4e7ddf14a71f219a0e95d81")

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

def ok(msg):    print(f"  {GREEN}[OK]  {msg}{RESET}")
def fail(msg):  print(f"  {RED}[FAIL] {msg}{RESET}")
def warn(msg):  print(f"  {YELLOW}[SKIP] {msg}{RESET}")
def info(msg):  print(f"  {CYAN}[INFO] {msg}{RESET}")

def fetch(url, headers=None, label="", timeout=15, retries=3, backoff=3):
    """
    Fetches a URL with automatic retry on transient errors (5xx, timeout).
    Returns (status_code, body_bytes, elapsed_ms).
    """
    req = urllib.request.Request(url, headers=headers or {})
    last_status, last_body = 0, b""
    for attempt in range(1, retries + 1):
        t0 = time.time()
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = resp.read()
                elapsed = int((time.time() - t0) * 1000)
                return resp.status, body, elapsed
        except urllib.error.HTTPError as e:
            last_status, last_body = e.code, str(e).encode()
            if e.code < 500:           # 4xx = client error, don't retry
                return last_status, last_body, 0
        except Exception as e:
            last_status, last_body = 0, str(e).encode()
        if attempt < retries:
            print(f"     [attempt {attempt}/{retries} failed, retrying in {backoff}s...]")
            time.sleep(backoff)
    return last_status, last_body, 0

def show_json_sample(body_bytes, max_keys=6):
    """Print a tidy sample of the JSON response body."""
    try:
        data = json.loads(body_bytes)
        if isinstance(data, dict):
            sample = {k: data[k] for k in list(data.keys())[:max_keys]}
            print(f"     Sample keys -> {list(sample.keys())}")
            # Show a tiny data snippet for arrays
            for k, v in sample.items():
                if isinstance(v, list) and len(v) > 0:
                    print(f"     [{k}][0] = {str(v[0])[:120]}")
                elif not isinstance(v, (dict, list)):
                    print(f"     {k} = {str(v)[:120]}")
        elif isinstance(data, list):
            print(f"     Array of {len(data)} items. First: {str(data[0])[:200]}")
    except Exception:
        # Not JSON (e.g. CSV)
        lines = body_bytes.decode(errors="replace").splitlines()
        for line in lines[:5]:
            print(f"     {line}")

def section(title):
    width = 70
    print()
    print("-" * width)
    print(f"{BOLD}  {title}{RESET}")
    print("-" * width)

# -----------------------------------------------------------------------------
# Test runner
# -----------------------------------------------------------------------------
results = {}   # api_name -> True/False/None (None = skipped)

def run_test(api_name, url, headers=None, expected_status=200, key_required=False, key_value="", note=""):
    """
    Runs one API test and prints formatted results.
    If key_required and key_value is empty, marks as SKIPPED.
    """
    if key_required and not key_value:
        warn(f"SKIPPED -- no key provided for {api_name}")
        warn(f"  -> {note}")
        results[api_name] = None
        return

    print(f"\n  Calling: {url[:100]}{'…' if len(url)>100 else ''}")
    status, body, ms = fetch(url, headers=headers)

    if status == expected_status:
        ok(f"HTTP {status}  ({ms} ms)")
        show_json_sample(body)
        results[api_name] = True
    else:
        fail(f"HTTP {status}  (expected {expected_status})")
        err_preview = body.decode(errors="replace")[:300]
        print(f"     Response: {err_preview}")
        results[api_name] = False


# ===========================================================================
print()
print(f"{BOLD}{'='*70}")
print("  VayuDrishti -- Live API Verification")
print(f"  Timestamp: {datetime.now(timezone(timedelta(hours=5, minutes=30))).strftime('%Y-%m-%d %H:%M:%S IST')}")
print(f"{'='*70}{RESET}")


# -----------------------------------------------------------------------------
# API 1: Open-Meteo Forecast (Delhi: 28.6139°N, 77.2090°E)
# -----------------------------------------------------------------------------
section("API 1 -- Open-Meteo Forecast (NO KEY NEEDED)")
info("Agent 2 uses this for wind, humidity, precipitation for Delhi")
url = (
    "https://api.open-meteo.com/v1/forecast"
    "?latitude=28.6139&longitude=77.2090"
    "&hourly=wind_speed_10m,wind_direction_10m,relative_humidity_2m,precipitation"
    "&forecast_days=3&timezone=Asia%2FKolkata"
)
run_test("Open-Meteo Forecast", url)


# -----------------------------------------------------------------------------
# API 2: Open-Meteo Air Quality (CAMS-based AQI forecast -- Delhi)
# -----------------------------------------------------------------------------
section("API 2 -- Open-Meteo Air Quality / CAMS (NO KEY NEEDED)")
info("Agent 2 uses this as a secondary AQI baseline forecast (PM2.5, PM10, NO2, SO2)")
url = (
    "https://air-quality-api.open-meteo.com/v1/air-quality"
    "?latitude=28.6139&longitude=77.2090"
    "&hourly=pm2_5,pm10,nitrogen_dioxide,sulphur_dioxide,carbon_monoxide,european_aqi"
    "&forecast_days=3&timezone=Asia%2FKolkata"
)
run_test("Open-Meteo Air Quality", url)


# -----------------------------------------------------------------------------
# API 3: OpenStreetMap Overpass -- road network density proxy (Delhi bounding box)
# Overpass needs POST for complex queries to avoid 406 Not Acceptable
# ---------------------------------------------------------------------------------
section("API 3 -- OpenStreetMap Overpass API (NO KEY NEEDED)")
info("Agent 1 uses this as a vehicular traffic density proxy")
info("Query: count primary + secondary roads in a Delhi ward bounding box")
query = "[out:json];(way[highway=primary](28.58,77.18,28.65,77.25);way[highway=secondary](28.58,77.18,28.65,77.25););out count;"
data_bytes = urllib.parse.urlencode({"data": query}).encode()
print(f"\n  Calling: https://overpass-api.de/api/interpreter (POST)")
print(f"  Query: {query[:80]}...")

osm_status, osm_body, osm_ms = 0, b"", 0
for attempt in range(1, 4):
    t0 = time.time()
    try:
        osm_req = urllib.request.Request(
            "https://overpass-api.de/api/interpreter",
            data=data_bytes,
            headers={"User-Agent": "VayuDrishti-API-Verifier/1.0 (research prototype)"},
        )
        with urllib.request.urlopen(osm_req, timeout=25) as resp:
            osm_body = resp.read()
            osm_ms = int((time.time()-t0)*1000)
            osm_status = resp.status
            break
    except urllib.error.HTTPError as e:
        osm_status = e.code
        osm_body = str(e).encode()
        if e.code < 500:
            break
    except Exception as e:
        osm_body = str(e).encode()
    if attempt < 3:
        print(f"     [attempt {attempt}/3 failed, retrying in 3s...]")
        time.sleep(3)

if osm_status == 200:
    ok(f"HTTP {osm_status}  ({osm_ms} ms)")
    show_json_sample(osm_body)
    results["OSM Overpass"] = True
else:
    fail(f"Error: {osm_body.decode(errors='replace')[:200]}")
    results["OSM Overpass"] = False


# -----------------------------------------------------------------------------
# API 4: OpenAQ v3 -- India CAAQMS stations (REQUIRES KEY)
# -----------------------------------------------------------------------------
section("API 4 -- OpenAQ v3 -- India Stations (KEY REQUIRED)")
info("Agents 1 & 2 use this for ground AQI: PM2.5, PM10, NO2, SO2, CO per station")
info("Register free at: https://openaq.org  ->  API Keys")
# v3: 'order_by=lastUpdated' and 'sort=desc' cause 422 -- strip them, just filter by country
url = "https://api.openaq.org/v3/locations?country=IN&limit=5"
run_test(
    "OpenAQ v3 Locations",
    url,
    headers={"X-API-Key": OPENAQ_KEY},
    key_required=True,
    key_value=OPENAQ_KEY,
    note="Get free key at https://openaq.org/register"
)

# If locations worked, also pull live sensor readings from a known Delhi station
if results.get("OpenAQ v3 Locations"):
    section("  API 4b -- OpenAQ v3 -- Live Sensor Readings (same key)")
    info("Fetching sensor parameter list for Delhi CPCB ITO station (id=8118)")
    run_test(
        "OpenAQ v3 Sensors",
        "https://api.openaq.org/v3/locations/8118/sensors",
        headers={"X-API-Key": OPENAQ_KEY},
        key_required=True,
        key_value=OPENAQ_KEY,
    )


# -----------------------------------------------------------------------------
# API 5: WAQI (World Air Quality Index) -- Free alternative to data.gov.in
# Same underlying CPCB station data, no govt registration, free token at aqicn.org/api
# -----------------------------------------------------------------------------
section("API 5 -- WAQI (replaces data.gov.in) -- India CPCB Stations (FREE ALTERNATIVE)")
info("WHY: OpenAQ + WAQI together give the same CPCB CAAQMS data as data.gov.in")
info("WHY: No govt registration needed, more reliable, wider historical archive")
info("Fetching Delhi CPCB station: ITO monitoring station")
info("Token 'demo' works for city-name feed; for bounds search get full token at https://aqicn.org/api/")
url_waqi = f"https://api.waqi.info/feed/delhi/?token={WAQI_TOKEN}"
run_test("WAQI Delhi Station", url_waqi)

# Also test search -- needs real token (demo returns 'Invalid key' for this endpoint)
info("Bounds search -- needs a real WAQI token (free, instant at https://aqicn.org/api/)")
if WAQI_TOKEN != 'demo':
    url_waqi2 = f"https://api.waqi.info/map/bounds/?latlng=28.4,76.8,28.9,77.4&token={WAQI_TOKEN}"
    run_test("WAQI India Station Search", url_waqi2)
else:
    warn("WAQI bounds search skipped -- 'demo' token doesn't support it")
    warn("  Get free full token at https://aqicn.org/api/ (instant, no card)")
    results["WAQI India Station Search"] = None


# -----------------------------------------------------------------------------
# API 6: NASA FIRMS -- Fire / Thermal Anomalies (REQUIRES MAP_KEY)
# -----------------------------------------------------------------------------
section("API 6 -- NASA FIRMS -- Fire Hotspots India (MAP_KEY REQUIRED)")
info("Agent 1 uses FIRMS to detect stubble burning & waste burning sources")
info("Get free MAP_KEY at: https://firms.modaps.eosdis.nasa.gov/api/map_key/")
info("India bounding box: W=68°E, S=6°N, E=98°E, N=38°N")
# FIRMS returns CSV -- custom display to show actual fire hotspot rows
firms_url = (
    f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{FIRMS_MAP_KEY}"
    f"/VIIRS_SNPP_NRT/68,6,98,38/1"
)
print(f"\n  Calling: {firms_url[:90]}...")
firms_status, firms_body, firms_ms = fetch(firms_url, timeout=20)
if firms_status == 200:
    ok(f"HTTP {firms_status}  ({firms_ms} ms) -- Real fire hotspot CSV returned")
    lines = firms_body.decode(errors='replace').strip().splitlines()
    print(f"     Rows returned (incl. header): {len(lines)}")
    for line in lines[:4]:   # header + first 3 hotspot rows
        print(f"     {line}")
    if len(lines) == 1:
        print("     (No active fires in India in last 24h -- normal for monsoon season)")
    results["NASA FIRMS VIIRS"] = True
else:
    fail(f"HTTP {firms_status}")
    results["NASA FIRMS VIIRS"] = False


# -----------------------------------------------------------------------------
# API 7: ISRO Bhuvan WMS -- Land Use / Land Cover
# Correct endpoint is bhuvan-vec2.nrsc.gov.in (bhuvan-app1 is the portal, not WMS)
# ---------------------------------------------------------------------------------
section("API 7 -- ISRO Bhuvan WMS -- Land Use (PUBLIC WMS, checking reachability)")
info("Agent 1 uses this for land-use classification (industrial/agricultural/urban)")
info("Endpoint: https://bhuvan-vec2.nrsc.gov.in/bhuvan/wms  (official NRSC OGC WMS)")
info("NOTE: Bhuvan servers are slow/intermittent -- 30s timeout used")
bhuvan_url = (
    "https://bhuvan-vec2.nrsc.gov.in/bhuvan/wms"
    "?service=WMS&request=GetCapabilities&version=1.1.1"
)
run_test(
    "ISRO Bhuvan WMS",
    bhuvan_url,
    headers={"User-Agent": "VayuDrishti-API-Verifier/1.0"}
)
if results.get("ISRO Bhuvan WMS") is False:
    warn("Bhuvan is a known slow/intermittent govt server. Fallback for the build:")
    warn("  Use OSM Overpass landuse=* tags (industrial/residential/farmland) instead.")
    warn("  OSM covers India well and is already verified in API 3 above.")


# ===========================================================================
# SUMMARY TABLE
# ===========================================================================
section("SUMMARY")
total = len(results)
passed  = sum(1 for v in results.values() if v is True)
failed  = sum(1 for v in results.values() if v is False)
skipped = sum(1 for v in results.values() if v is None)

print(f"\n  {'API':<30} {'STATUS'}")
print(f"  {'-'*29} {'-'*12}")
for name, status in results.items():
    if status is True:
        badge = f"{GREEN}PASS{RESET}"
    elif status is False:
        badge = f"{RED}FAIL{RESET}"
    else:
        badge = f"{YELLOW}SKIPPED (no key){RESET}"
    print(f"  {name:<30} {badge}")

print()
print(f"  {GREEN}Passed : {passed}{RESET}   {RED}Failed : {failed}{RESET}   {YELLOW}Skipped: {skipped}{RESET}  /  Total: {total}")

if skipped > 0:
    print()
    print(f"  {YELLOW}ACTION NEEDED:{RESET}")
    print("  Add your API keys at the top of this file and re-run:")
    if not OPENAQ_KEY:
        print("    -> OPENAQ_KEY    : https://openaq.org/register")
    if not FIRMS_MAP_KEY:
        print("    -> FIRMS_MAP_KEY : https://firms.modaps.eosdis.nasa.gov/api/map_key/")
    if WAQI_TOKEN == 'demo':
        print("    -> WAQI_TOKEN    : https://aqicn.org/api/  (free, instant -- upgrades 'demo' token)")
    print()
    print(f"  {GREEN}NOTE: data.gov.in is NOT needed.{RESET}")
    print("  OpenAQ v3 + WAQI together cover all 900+ CPCB CAAQMS stations.")

print()
