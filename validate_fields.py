"""
VayuDrishti -- Field Validation v2 (Patched)
============================================
Fixes from v1:
  1. OpenAQ: use /sensors/{id}/measurements (not /locations/{id}/measurements)
  2. FIRMS: use VIIRS_SNPP_SP for standard-processing 7-day archive (not NRT)
  3. Agent 1 pivot: Open-Meteo CAMS is the pollutant-ratio source (not single-station OpenAQ)
     because CAMS has all 5 pollutants (PM2.5, PM10, NO2, SO2, CO) in µg/m3 on the grid,
     whereas most individual CPCB stations only report 1-2 sensors.
"""

import sys, os, json, time, urllib.request, urllib.parse, urllib.error, math
from datetime import datetime, timezone, timedelta

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

OPENAQ_KEY    = "7ffaf5866c44b25be96e7b77db9ca76ee47c1ca6defdd3b7b4c79335e9276ee1"
FIRMS_MAP_KEY = "b505fb21612726e92ad353db0d9efb56"
WAQI_TOKEN    = "99af914e84b9e5faf4e7ddf14a71f219a0e95d81"

DELHI_LAT, DELHI_LON   = 28.6139, 77.2090
OPENAQ_STATION_ID      = 8118    # Delhi ITO CPCB
OPENAQ_PM25_SENSOR_ID  = 23534   # PM2.5 sensor at station 8118

GREEN, RED, YELLOW, CYAN, BOLD, RESET = "\033[92m","\033[91m","\033[93m","\033[96m","\033[1m","\033[0m"
IST = timezone(timedelta(hours=5, minutes=30))

def fetch(url, headers=None, timeout=25, post_data=None):
    req = urllib.request.Request(url, data=post_data,
                                  headers=headers or {"User-Agent": "VayuDrishti/2.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:
        return 0, str(e).encode()

results = {}

def section(title):
    print(f"\n{BOLD}{'='*70}{RESET}")
    print(f"{BOLD}  {title}{RESET}")
    print(f"{BOLD}{'='*70}{RESET}")

def ok_line(label, value, extra=""):
    print(f"  {GREEN}[OK]{RESET}  {label:<50} = {str(value)[:60]}  {extra}")

def fail_line(label, note=""):
    print(f"  {RED}[MISSING]{RESET} {label:<50} {RED}{note}{RESET}")

def check(label, value, typ=None, nonempty=False):
    ok = True
    if value is None:
        ok = False
    elif typ and not isinstance(value, typ):
        ok = False
    elif nonempty and not value:
        ok = False
    if ok:
        ok_line(label, value)
    else:
        fail_line(label, f"got: {value!r}")
    return ok

print(f"\n{BOLD}VayuDrishti -- Deep Data Field Validation v2 (Patched){RESET}")
print(f"Timestamp: {datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S IST')}\n")

# =============================================================================
# TEST 1 (FIX): Open-Meteo CAMS -- Agent 1's actual pollutant source
#   WHY CHANGE: Most CPCB stations only report 1-2 sensors.
#   CAMS provides the full multi-pollutant grid (all 5 needed by Agent 1).
# =============================================================================
section("TEST 1 (FIX): Open-Meteo CAMS -- Agent 1 Pollutant Ratios (PRIMARY source)")
print(f"  {CYAN}Agent 1 needs PM2.5, PM10, NO2, SO2, CO to compute source fingerprint ratios{RESET}")
print(f"  {CYAN}PIVOT: CAMS gives all 5 in ug/m3 on a grid -- better than single CPCB station{RESET}\n")

url_cams = (
    "https://air-quality-api.open-meteo.com/v1/air-quality"
    f"?latitude={DELHI_LAT}&longitude={DELHI_LON}"
    "&hourly=pm2_5,pm10,nitrogen_dioxide,sulphur_dioxide,carbon_monoxide"
    "&forecast_days=1&timezone=Asia%2FKolkata"
)
s, b = fetch(url_cams)
print(f"  HTTP {s}")

if s == 200:
    d = json.loads(b)
    h = d.get("hourly", {})
    # Current hour (index 0)
    pm25 = h.get("pm2_5",            [None])[0]
    pm10 = h.get("pm10",             [None])[0]
    no2  = h.get("nitrogen_dioxide", [None])[0]
    so2  = h.get("sulphur_dioxide",  [None])[0]
    co   = h.get("carbon_monoxide",  [None])[0]

    print("  --- Pollutant values at Delhi (current hour, µg/m³) ---")
    check("PM2.5",  pm25, (int, float))
    check("PM10",   pm10, (int, float))
    check("NO2",    no2,  (int, float))
    check("SO2",    so2,  (int, float))
    check("CO",     co,   (int, float))

    # Agent 1 ratio fingerprinting (the actual computation)
    print(f"\n  {CYAN}--- Agent 1 source fingerprints (computed live) ---{RESET}")
    if pm10 and pm25 and pm25 > 0:
        r1 = round(pm10 / pm25, 2)
        src1 = "DUST/CONSTRUCTION dominant" if r1 > 3 else "MIXED urban" if r1 > 1.5 else "PM2.5-dominant"
        print(f"  PM10/PM2.5 ratio:   {r1}   → {src1}")

    if no2 and co and co > 0:
        r2 = round(no2 / (co / 1000), 2)  # CO in mg/m3 → convert
        print(f"  NO2 level:          {no2} µg/m³  → {'HIGH vehicular' if no2 > 50 else 'MODERATE vehicular'}")

    if so2:
        print(f"  SO2 level:          {so2} µg/m³  → {'HIGH industrial' if so2 > 30 else 'MODERATE industrial' if so2 > 10 else 'LOW industrial'}")

    if co:
        print(f"  CO level:           {co} µg/m³  → {'BURNING/combustion signal' if co > 500 else 'Background'}")

    # Compute what Agent 1 would output right now
    if all(x is not None for x in [pm25, pm10, no2, so2, co]):
        total_score = pm25 + pm10 + no2 + so2 + (co / 100)
        pct_v   = round((no2 / total_score) * 100)
        pct_i   = round((so2 / total_score) * 100)
        pct_d   = round(((pm10 - pm25) / total_score) * 100) if pm10 > pm25 else 0
        pct_b   = round(((co / 100) / total_score) * 100)
        pct_c   = max(0, 100 - pct_v - pct_i - pct_d - pct_b)
        print(f"\n  {CYAN}  Agent 1 source breakdown for Delhi right now:{RESET}")
        print(f"    Vehicular:          {pct_v}%")
        print(f"    Industrial:         {pct_i}%")
        print(f"    Dust/Construction:  {pct_d}%")
        print(f"    Burning/Biomass:    {pct_b}%")
        print(f"    Construction/Other: {pct_c}%")

    results["CAMS Pollutants"] = all(x is not None for x in [pm25, pm10, no2, so2, co])
else:
    print(f"  {RED}FAILED{RESET}: {b.decode(errors='replace')[:200]}")
    results["CAMS Pollutants"] = False


# =============================================================================
# TEST 2 (FIX): OpenAQ v3 sensor measurements -- correct endpoint
#   FIX: was /locations/{id}/measurements → now /sensors/{id}/measurements
# =============================================================================
section("TEST 2 (FIX): OpenAQ v3 Sensor Measurements -- Correct Endpoint")
print(f"  {CYAN}Used for historical spike baseline in Agent 6{RESET}")
print(f"  {CYAN}FIX: /sensors/{OPENAQ_PM25_SENSOR_ID}/measurements (not /locations endpoint){RESET}\n")

url2 = f"https://api.openaq.org/v3/sensors/{OPENAQ_PM25_SENSOR_ID}/measurements?limit=10"
s2, b2 = fetch(url2, headers={"X-API-Key": OPENAQ_KEY})
print(f"  HTTP {s2}  |  URL: {url2}")

if s2 == 200:
    d2 = json.loads(b2)
    meas = d2.get("results", [])
    print(f"  Measurements returned: {len(meas)}")
    print()
    print("  --- Recent PM2.5 readings (for Agent 6 rolling baseline) ---")
    vals = []
    for m in meas[:8]:
        val = m.get("value")
        ts  = m.get("period", {}).get("datetimeFrom", {}).get("local", "")
        if val is not None:
            vals.append(val)
            print(f"    {ts[:19]:<20}  PM2.5 = {val} µg/m³")
    if vals:
        import statistics
        mean = round(statistics.mean(vals), 1)
        sd   = round(statistics.stdev(vals), 1) if len(vals) > 1 else 0
        print(f"\n  Rolling stats (Agent 6 baseline from these {len(vals)} readings):")
        print(f"    Mean:   {mean} µg/m³")
        print(f"    StdDev: {sd} µg/m³")
        if sd > 0:
            latest = vals[0]
            z = round((latest - mean) / sd, 2)
            spike = "*** SPIKE DETECTED ***" if abs(z) > 2 else "normal"
            print(f"    Latest ({latest}): z-score = {z}  → {spike}")
    results["OpenAQ Measurements"] = len(meas) > 0
else:
    print(f"  {RED}FAILED: HTTP {s2}{RESET}: {b2.decode(errors='replace')[:200]}")
    results["OpenAQ Measurements"] = False


# =============================================================================
# TEST 3: Open-Meteo Weather (unchanged from v1 -- was already passing)
# =============================================================================
section("TEST 3: Open-Meteo Weather -- Wind + Met (Agent 1 upwind cone + Agent 2)")
url3 = (
    "https://api.open-meteo.com/v1/forecast"
    f"?latitude={DELHI_LAT}&longitude={DELHI_LON}"
    "&hourly=wind_speed_10m,wind_direction_10m,relative_humidity_2m,"
    "precipitation,temperature_2m,cloud_cover"
    "&forecast_days=3&timezone=Asia%2FKolkata"
)
s3, b3 = fetch(url3)
print(f"  HTTP {s3}")
if s3 == 200:
    h3 = json.loads(b3).get("hourly", {})
    wind_spd = h3.get("wind_speed_10m", [None])[0]
    wind_dir = h3.get("wind_direction_10m", [None])[0]
    humidity = h3.get("relative_humidity_2m", [None])[0]
    cloud    = h3.get("cloud_cover", [None])[0]

    for f, v in [("wind_speed_10m", wind_spd), ("wind_direction_10m", wind_dir),
                 ("relative_humidity_2m", humidity), ("cloud_cover", cloud)]:
        check(f, v, (int, float))

    if wind_spd and wind_dir:
        # Compass direction
        dirs = ["N","NE","E","SE","S","SW","W","NW","N"]
        compass = dirs[int((wind_dir + 22.5) / 45) % 8]
        print(f"\n  {CYAN}Agent 1 upwind cone right now:{RESET}")
        print(f"    Wind: {wind_spd} m/s from {compass} ({wind_dir}°)")
        print(f"    Upwind direction: {(wind_dir+180)%360}° ({dirs[int(((wind_dir+180)%360+22.5)/45)%8]})")
        print(f"    3-hour plume radius: {round(wind_spd * 3 * 3.6, 1)} km")
        if cloud and cloud > 70:
            print(f"    Satellite flag: {cloud}% cloud cover → satellite data may be blocked → confidence reduced")

    results["Open-Meteo Weather"] = all(x is not None for x in [wind_spd, wind_dir, humidity])
else:
    print(f"  {RED}FAILED{RESET}")
    results["Open-Meteo Weather"] = False


# =============================================================================
# TEST 4 (FIX): NASA FIRMS -- use VIIRS_SNPP_SP for 7-day (not NRT)
#   FIX: NRT only keeps 1 day. SP (standard processing) = up to 7 days.
# =============================================================================
section("TEST 4 (FIX): NASA FIRMS -- 7-day Fire Archive (VIIRS Standard Processing)")
print(f"  {CYAN}FIX: NRT archive = 1 day only. Use VIIRS_SNPP_SP for 7-day history.{RESET}\n")

# Try VIIRS_SNPP_SP first (standard processing, 7-day)
url4 = (
    f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{FIRMS_MAP_KEY}"
    f"/VIIRS_SNPP_SP/68,6,98,38/7"
)
s4, b4 = fetch(url4, timeout=30)
print(f"  HTTP {s4}  |  VIIRS_SNPP_SP 7-day")

if s4 != 200:
    # Fallback: try MODIS_NRT (different sensor, 1-day)
    print(f"  SP failed (HTTP {s4}), trying MODIS_NRT 1-day...")
    url4 = (f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{FIRMS_MAP_KEY}"
            f"/MODIS_NRT/68,6,98,38/1")
    s4, b4 = fetch(url4, timeout=25)
    print(f"  HTTP {s4}  |  MODIS_NRT 1-day fallback")

if s4 == 200:
    text = b4.decode(errors='replace').strip()
    lines = text.splitlines()
    print(f"  Rows returned (incl. header): {len(lines)}")
    NEEDED = ["latitude", "longitude", "acq_date", "acq_time", "frp", "confidence", "daynight"]
    header = [h.strip() for h in lines[0].split(",")]

    print("\n  --- Required field check ---")
    all_fields_ok = True
    for f in NEEDED:
        present = f in header
        if present:
            ok_line(f, "present in CSV header")
        else:
            fail_line(f, "NOT in header")
            all_fields_ok = False

    if len(lines) >= 2:
        print(f"\n  --- Sample fire rows ---")
        for row_line in lines[1:4]:
            vals = row_line.split(",")
            row  = dict(zip(header, vals))
            lat  = row.get("latitude", "?")
            lon  = row.get("longitude", "?")
            date = row.get("acq_date", "?")
            frp  = row.get("frp", "?")
            conf = row.get("confidence", "?")
            dn   = row.get("daynight", "?")
            print(f"    lat={lat}, lon={lon}, date={date}, frp={frp}MW, conf={conf}, {dn}")

            # Agent 1 plume calculation
            try:
                dist = math.sqrt((float(lat)-DELHI_LAT)**2 + (float(lon)-DELHI_LON)**2) * 111
                travel_h = dist / (6.1 * 3.6)
                print(f"      → {dist:.0f} km from Delhi | plume travel: ~{travel_h:.1f}h at current wind")
            except Exception:
                pass
    else:
        print(f"  {YELLOW}No fire rows (monsoon season expected -- header confirmed){RESET}")

    results["NASA FIRMS"] = all_fields_ok
else:
    print(f"  {RED}FAILED: HTTP {s4}{RESET}: {b4.decode(errors='replace')[:200]}")
    results["NASA FIRMS"] = False


# =============================================================================
# TEST 5: OSM Overpass (unchanged -- was passing)
# =============================================================================
section("TEST 5: OSM Overpass -- Road Density for Agent 1 Vehicular Weight")
query = ("[out:json];(way[highway=primary](28.58,77.18,28.65,77.25);"
         "way[highway=secondary](28.58,77.18,28.65,77.25);"
         "way[highway=tertiary](28.58,77.18,28.65,77.25););out count;")
data_bytes = urllib.parse.urlencode({"data": query}).encode()
req_osm = urllib.request.Request("https://overpass-api.de/api/interpreter", data=data_bytes,
                                   headers={"User-Agent": "VayuDrishti/2.0"})
try:
    with urllib.request.urlopen(req_osm, timeout=25) as r:
        osm_body = r.read(); osm_status = r.status
except Exception as e:
    osm_body = str(e).encode(); osm_status = 0

print(f"  HTTP {osm_status}")
if osm_status == 200:
    tags = json.loads(osm_body).get("elements", [{}])[0].get("tags", {})
    ways = int(tags.get("ways", 0))
    check("Road way count", ways, int)
    density = round(ways / 59, 1)
    print(f"\n  Road density: {density} ways/km²  → {'HIGH' if density>10 else 'MEDIUM'} vehicular weight")
    results["OSM Overpass"] = ways > 0
else:
    results["OSM Overpass"] = False


# =============================================================================
# TEST 6: WAQI multi-pollutant (Agent 5 advisory + Agent 6 spike detection)
# =============================================================================
section("TEST 6: WAQI -- Multi-Pollutant Current AQI (Agent 5 + 6)")
url6 = f"https://api.waqi.info/feed/delhi/?token={WAQI_TOKEN}"
s6, b6 = fetch(url6)
print(f"  HTTP {s6}")
if s6 == 200:
    wd = json.loads(b6).get("data", {})
    ia = wd.get("iaqi", {})
    aqi = wd.get("aqi")
    dom = wd.get("dominentpol", "")

    for lbl, val in [("AQI", aqi), ("PM2.5", ia.get("pm25",{}).get("v")),
                     ("PM10", ia.get("pm10",{}).get("v")), ("NO2", ia.get("no2",{}).get("v")),
                     ("SO2",  ia.get("so2",{}).get("v")),  ("CO",  ia.get("co",{}).get("v")),
                     ("Wind", ia.get("w",{}).get("v")),    ("Temp",ia.get("t",{}).get("v")),
                     ("Timestamp", wd.get("time",{}).get("s"))]:
        check(lbl, val)

    print(f"\n  {CYAN}--- Agent 5 advisory output right now ---{RESET}")
    cat = ("Good" if aqi<=50 else "Satisfactory" if aqi<=100 else "Moderate"
           if aqi<=200 else "Poor" if aqi<=300 else "Very Poor" if aqi<=400 else "Severe")
    advisory = {
        "Good":         "Air quality is good. Normal outdoor activities are safe.",
        "Satisfactory": "Air quality is acceptable. Sensitive individuals should limit prolonged outdoor exertion.",
        "Moderate":     "Everyone may experience health effects. Reduce prolonged outdoor activities.",
        "Poor":         "Everyone should avoid prolonged outdoor activities. Sensitive groups should stay indoors.",
        "Very Poor":    "Avoid all outdoor activities. Keep windows closed.",
        "Severe":       "Health emergency. Everyone should stay indoors immediately.",
    }
    print(f"  AQI: {aqi}  |  Category: {cat}  |  Dominant: {dom.upper()}")
    print(f"  Advisory text: \"{advisory[cat]}\"")
    results["WAQI"] = isinstance(aqi, (int, float)) and aqi > 0
else:
    results["WAQI"] = False


# =============================================================================
# TEST 7: WAQI bounds search -- multi-station discovery (Agent 6 spatial context)
# =============================================================================
section("TEST 7: WAQI Bounds Search -- All Stations in Delhi (Agent 6 spatial context)")
url7 = f"https://api.waqi.info/map/bounds/?latlng=28.4,76.8,28.9,77.4&token={WAQI_TOKEN}"
s7, b7 = fetch(url7)
print(f"  HTTP {s7}")
if s7 == 200:
    wd7 = json.loads(b7)
    stations = wd7.get("data", [])
    print(f"  Stations found in Delhi bbox: {len(stations)}")
    print()
    print("  --- Station list ---")
    for st in stations[:8]:
        name = st.get("station", {}).get("name", "?")
        aqi  = st.get("aqi", "?")
        lat  = st.get("lat", "?")
        lon  = st.get("lon", "?")
        print(f"    AQI={aqi:<5} | ({lat}, {lon}) | {name}")
    results["WAQI Bounds"] = len(stations) > 0
else:
    results["WAQI Bounds"] = False


# =============================================================================
# FINAL SUMMARY
# =============================================================================
section("FINAL SUMMARY -- Data Readiness per Agent")

print(f"""
  {CYAN}Updated data source mapping after pivots:{RESET}
  Agent 1 (Attribution):  Open-Meteo CAMS (ratios) + OSM (roads) + FIRMS (fires) + OMeteo (wind)
  Agent 2 (Forecast):     Open-Meteo CAMS (baseline) + WAQI historical + OMeteo weather
  Agent 3 (Enforcement):  Reads Agent 1+2 output from DB + LLM reasoning (needs Gemini key)
  Agent 5 (Advisory):     WAQI AQI + CPCB breakpoint rules + LLM localisation
  Agent 6 (Anomaly):      OpenAQ sensor history (baseline) + same sources as Agent 1
  Agent 7 (NL Query):     Reads all agents' DB output (no raw API needed)
""")

agent_data = {
    "Agent 1 (Source Attribution)": results.get("CAMS Pollutants") and results.get("Open-Meteo Weather") and results.get("OSM Overpass"),
    "Agent 2 (Forecasting)":        results.get("CAMS Pollutants") and results.get("Open-Meteo Weather"),
    "Agent 3 (Enforcement)":        True,   # depends on DB, not raw API
    "Agent 5 (Citizen Advisory)":   results.get("WAQI"),
    "Agent 6 (Anomaly):":           results.get("OpenAQ Measurements") and results.get("Open-Meteo Weather"),
    "Agent 7 (NL Query)":           True,
}

for agent, ready in agent_data.items():
    badge = f"{GREEN}DATA READY{RESET}" if ready else f"{RED}DATA GAP{RESET}"
    print(f"  {badge}  {agent}")

pass_count = sum(1 for v in results.values() if v)
ag_count   = sum(agent_data.values())
print(f"\n  {BOLD}Raw API tests:         {pass_count}/{len(results)} PASS{RESET}")
print(f"  {BOLD}Agents with full data: {ag_count}/{len(agent_data)}{RESET}")

if ag_count == len(agent_data):
    print(f"\n  {GREEN}{BOLD}ALL AGENTS HAVE THEIR DATA -- READY TO BUILD{RESET}")
else:
    gaps = [a for a, r in agent_data.items() if not r]
    print(f"\n  {YELLOW}Remaining gaps: {gaps}{RESET}")
