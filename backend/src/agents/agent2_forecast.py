import json
from datetime import datetime, timedelta
from src.db.session import SessionLocal
from src.db.models import City, RawWeather, RawAQIReading, ForecastGrid, Station, Ward
from src.ingestion.aqi_calculator import calculate_indian_aqi

AQI_MIN, AQI_MAX = 5, 500  # valid Indian AQI range — forecasts must stay inside


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))

def get_future_weather(db, city_id, hours_ahead):
    """Fetch the weather forecast for X hours ahead by looking at the timestamp."""
    target_time = datetime.utcnow() + timedelta(hours=hours_ahead)
    
    # In SQLite, we can just grab the closest one in the future
    # For MVP, we will sort by timestamp descending and try to find the one closest to target
    # Alternatively, just fetch all future weather and pick the one with matching hour gap roughly
    future_weathers = db.query(RawWeather).filter(
        RawWeather.city_id == city_id,
        RawWeather.timestamp > datetime.utcnow()
    ).order_by(RawWeather.timestamp.asc()).all()
    
    # Find closest to target_time
    closest = None
    min_diff = timedelta(days=365)
    for w in future_weathers:
        diff = abs(w.timestamp - target_time)
        if diff < min_diff:
            min_diff = diff
            closest = w
            
    return closest

def run_agent_2(ward_id: int):
    print(f"Starting Agent 2 for Ward ID: {ward_id}")
    db = SessionLocal()
    
    ward = db.query(Ward).filter_by(ward_id=ward_id).first()
    if not ward:
        return
        
    city = db.query(City).filter_by(city_id=ward.city_id).first()
    
    # Get current AQI
    station = db.query(Station).filter_by(ward_id=ward_id).first()
    latest_aqi = db.query(RawAQIReading).filter_by(station_id=station.station_id).order_by(RawAQIReading.timestamp.desc()).first() if station else None
    
    if not latest_aqi:
        print("No current AQI found to baseline off of. Run live telemetry first.")
        return

    # Baseline off the REAL current AQI (Indian CPCB formula), not a raw
    # concentration average. This is the value the map/panel also shows.
    co_mg = latest_aqi.co / 1000.0 if latest_aqi.co else 0
    current_aqi_val, dom = calculate_indian_aqi(latest_aqi.pm25, latest_aqi.pm10, latest_aqi.no2, latest_aqi.so2, co_mg)
    current_aqi_val = _clamp(current_aqi_val, AQI_MIN, AQI_MAX)
    print(f"Current Baseline AQI: {current_aqi_val} (dominant {dom})")

    # Prefer Google's authoritative 96h hourly forecast (India CPCB AQI) when a
    # key is configured. Falls through to the physics-drift model otherwise.
    from src.ingestion.google_air_quality import has_google_key, fetch_forecast, extract_india_aqi
    if has_google_key() and station and station.lat and station.lon:
        gf = fetch_forecast(station.lat, station.lon, hours=72)
        hourly = (gf or {}).get("hourlyForecasts", [])
        if hourly:
            made_at = datetime.utcnow()
            wrote = 0
            for horizon in [24, 48, 72]:
                idx = min(horizon, len(hourly) - 1)
                aqi_g, dom_g = extract_india_aqi(hourly[idx])
                if aqi_g is None:
                    continue
                drift = round(aqi_g - current_aqi_val)
                uncertainty = round(aqi_g * (0.05 + horizon / 240.0))
                db.add(ForecastGrid(
                    city_id=city.city_id, grid_cell_id=f"{city.name[:3].upper()}-G",
                    forecast_made_at=made_at, horizon_hours=horizon, aqi_predicted=aqi_g,
                    uncertainty_band=uncertainty, physics_component=drift, ml_component=1.0,
                ))
                wrote += 1
                print(f"[Google forecast] {horizon}h AQI={aqi_g} (dominant {dom_g})")
            if wrote:
                db.commit()
                db.close()
                print("Agent 2 used Google Air Quality forecast.")
                return

    # Current weather as the reference point for meteorological *change*.
    current_weather = db.query(RawWeather).filter(
        RawWeather.city_id == city.city_id,
        RawWeather.timestamp <= datetime.utcnow()
    ).order_by(RawWeather.timestamp.desc()).first()
    ref_wind = current_weather.wind_speed if current_weather and current_weather.wind_speed is not None else 10.0
    ref_temp = current_weather.temp if current_weather and current_weather.temp is not None else 25.0

    for horizon in [24, 48, 72]:
        future_weather = get_future_weather(db, city.city_id, horizon)

        if not future_weather:
            print(f"No future weather found for {horizon}h. Skipping.")
            continue

        print(f"\n--- {horizon}h Forecast ---")
        print(f"Predicted Weather -> Wind: {future_weather.wind_speed} km/h, Temp: {future_weather.temp} C")

        # Bounded meteorological adjustment as a PERCENTAGE of the current AQI:
        #   - stronger future wind than now disperses pollution (lowers AQI)
        #   - colder than now => thermal inversion traps pollution (raises AQI)
        # Each effect capped so a forecast can never explode or collapse.
        wind_delta = (future_weather.wind_speed or ref_wind) - ref_wind
        temp_delta = ref_temp - (future_weather.temp if future_weather.temp is not None else ref_temp)
        wind_pct = _clamp(-wind_delta * 0.015, -0.25, 0.25)   # +wind => negative => lower AQI
        temp_pct = _clamp(temp_delta * 0.010, -0.20, 0.20)    # colder => positive => higher AQI
        drift_pct = _clamp(wind_pct + temp_pct, -0.35, 0.35)

        predicted_aqi = _clamp(round(current_aqi_val * (1 + drift_pct)), AQI_MIN, AQI_MAX)
        drift = predicted_aqi - current_aqi_val

        # Uncertainty band grows with horizon (~10% at 24h up to ~30% at 72h)
        uncertainty = round(predicted_aqi * (0.05 + (horizon / 240.0)))

        print(f"Predicted AQI: {predicted_aqi} (drift {drift:+d}) +/-{uncertainty}")

        forecast = ForecastGrid(
            city_id=city.city_id,
            grid_cell_id=f"{city.name[:3].upper()}-1",
            forecast_made_at=datetime.utcnow(),
            horizon_hours=horizon,
            aqi_predicted=predicted_aqi,
            uncertainty_band=uncertainty,
            physics_component=drift,
            ml_component=0.0
        )
        db.add(forecast)
        
    db.commit()
    print("\nSuccessfully wrote Agent 2 forecast results to the database.")
    db.close()

if __name__ == "__main__":
    import sys
    ward_id = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    run_agent_2(ward_id)
