import requests
from datetime import datetime, timedelta
from src.db.session import SessionLocal
from src.db.models import City, Ward, Station, RawWeather, RawAQIReading

# Network timeout for every external call — without this a slow/rate-limited
# API hangs the whole ingestion and endpoints silently fall back to stale rows.
HTTP_TIMEOUT = 15


def ensure_station_exists(db, ward, lat, lon):
    station = db.query(Station).filter_by(ward_id=ward.ward_id).first()
    if not station:
        station = Station(ward_id=ward.ward_id, name=f"{ward.name} Monitor", lat=lat, lon=lon, source="Open-Meteo API")
        db.add(station)
        db.commit()
    return station


def _nearest_index(times, target):
    """Index of the hourly timestamp closest to `target` (a datetime).

    Open-Meteo returns hours starting at today 00:00 UTC, so the current hour is
    somewhere in the middle — never assume index 0. Returns None if unparseable.
    """
    best_idx, best_diff = None, None
    for i, t in enumerate(times):
        try:
            dt = datetime.fromisoformat(t)
        except (ValueError, TypeError):
            continue
        diff = abs((dt - target).total_seconds())
        if best_diff is None or diff < best_diff:
            best_idx, best_diff = i, diff
    return best_idx


def fetch_live_telemetry(db, city: City, ward: Ward, lat: float, lon: float):
    """Fetches real weather AND real AQI for the given coordinates.

    Returns a status dict so callers know whether live data actually arrived:
        {"aqi_ok": bool, "weather_ok": bool, "error": str|None}
    On failure it does NOT insert placeholder/default rows — the freshness guard
    in the API layer then reports "no live data" instead of showing stale data.
    """
    station = ensure_station_exists(db, ward, lat, lon)
    status = {"aqi_ok": False, "weather_ok": False, "error": None}
    now = datetime.utcnow()

    # 1. Fetch Weather --------------------------------------------------------
    weather_url = (
        f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
        "&current_weather=true&timezone=GMT"
        "&hourly=temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,wind_direction_10m"
    )
    try:
        w_res = requests.get(weather_url, timeout=HTTP_TIMEOUT).json()
        current_w = w_res.get("current_weather", {})
        hourly_w = w_res.get("hourly", {})

        if current_w:
            db.add(RawWeather(
                city_id=city.city_id, timestamp=now,
                wind_speed=current_w.get("windspeed", 0.0),
                wind_dir=current_w.get("winddirection", 0.0),
                temp=current_w.get("temperature", 25.0),
                humidity=0.0, precipitation=0.0,
            ))
            status["weather_ok"] = True

        # Forecasts: anchor each horizon to (now + H hours), not to array index H.
        w_times = hourly_w.get("time", [])
        if w_times:
            for hours_ahead in [24, 48, 72]:
                idx = _nearest_index(w_times, now + timedelta(hours=hours_ahead))
                if idx is None:
                    continue
                try:
                    dt = datetime.fromisoformat(w_times[idx])
                except (ValueError, TypeError):
                    continue
                db.add(RawWeather(
                    city_id=city.city_id, timestamp=dt,
                    wind_speed=hourly_w["wind_speed_10m"][idx],
                    wind_dir=hourly_w["wind_direction_10m"][idx],
                    temp=hourly_w["temperature_2m"][idx],
                    humidity=hourly_w["relative_humidity_2m"][idx],
                    precipitation=hourly_w["precipitation"][idx],
                ))
    except Exception as e:
        status["error"] = f"weather: {e}"
        print(f"Error fetching weather for {city.name}: {e}")

    # 2. Fetch Air Quality ----------------------------------------------------
    aqi_url = (
        f"https://air-quality-api.open-meteo.com/v1/air-quality?latitude={lat}&longitude={lon}"
        "&timezone=GMT&hourly=pm10,pm2_5,nitrogen_dioxide,sulphur_dioxide,carbon_monoxide"
    )
    try:
        a_res = requests.get(aqi_url, timeout=HTTP_TIMEOUT).json()
        hourly_a = a_res.get("hourly", {})
        times = hourly_a.get("time", [])

        idx = _nearest_index(times, now) if times else None
        if idx is not None:
            pm25 = hourly_a["pm2_5"][idx]
            pm10 = hourly_a["pm10"][idx]
            no2 = hourly_a["nitrogen_dioxide"][idx]
            so2 = hourly_a["sulphur_dioxide"][idx]
            co = hourly_a["carbon_monoxide"][idx]

            # Require at least the primary pollutant. If the region has no real
            # PM data, fail loudly rather than fabricate a default reading.
            if pm25 is None and pm10 is None:
                status["error"] = "aqi: no PM data for this region"
                print(f"No live AQI (PM) data available for {city.name} — skipping insert.")
            else:
                db.add(RawAQIReading(
                    station_id=station.station_id,
                    timestamp=now,
                    pm25=pm25 if pm25 is not None else (pm10 if pm10 is not None else 0.0),
                    pm10=pm10 if pm10 is not None else (pm25 if pm25 is not None else 0.0),
                    no2=no2 if no2 is not None else 0.0,
                    so2=so2 if so2 is not None else 0.0,
                    co=co if co is not None else 0.0,
                    source="Open-Meteo",
                ))
                status["aqi_ok"] = True
        else:
            status["error"] = "aqi: empty response for this region"
            print(f"Empty AQI response for {city.name} — skipping insert.")
    except Exception as e:
        status["error"] = f"aqi: {e}"
        print(f"Error fetching AQI for {city.name}: {e}")

    db.commit()
    print(f"Telemetry for {city.name}: aqi_ok={status['aqi_ok']} weather_ok={status['weather_ok']}")
    return status
