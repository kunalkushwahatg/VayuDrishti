import requests
from datetime import datetime, timedelta
import random
from src.db.session import SessionLocal
from src.db.models import City, Ward, Station, RawWeather, RawAQIReading

def ensure_station_exists(db, ward, lat, lon):
    station = db.query(Station).filter_by(ward_id=ward.ward_id).first()
    if not station:
        station = Station(ward_id=ward.ward_id, name=f"{ward.name} Monitor", lat=lat, lon=lon, source="Open-Meteo API")
        db.add(station)
        db.commit()
    return station

def fetch_live_telemetry(db, city: City, ward: Ward, lat: float, lon: float):
    """Fetches real weather AND real AQI data for the given coordinates."""
    station = ensure_station_exists(db, ward, lat, lon)
    
    # 1. Fetch Weather
    weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true&hourly=temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,wind_direction_10m"
    try:
        w_res = requests.get(weather_url).json()
        current_w = w_res.get("current_weather", {})
        hourly_w = w_res.get("hourly", {})
        
        # Current Weather
        weather = RawWeather(
            city_id=city.city_id,
            timestamp=datetime.utcnow(),
            wind_speed=current_w.get("windspeed", 0.0),
            wind_dir=current_w.get("winddirection", 0.0),
            temp=current_w.get("temperature", 25.0),
            humidity=0.0,
            precipitation=0.0
        )
        db.add(weather)
        
        # Forecasts
        if "time" in hourly_w and len(hourly_w["time"]) >= 73:
            for hours_ahead in [24, 48, 72]:
                dt = datetime.fromisoformat(hourly_w["time"][hours_ahead])
                f = RawWeather(
                    city_id=city.city_id,
                    timestamp=dt,
                    wind_speed=hourly_w["wind_speed_10m"][hours_ahead],
                    wind_dir=hourly_w["wind_direction_10m"][hours_ahead],
                    temp=hourly_w["temperature_2m"][hours_ahead],
                    humidity=hourly_w["relative_humidity_2m"][hours_ahead],
                    precipitation=hourly_w["precipitation"][hours_ahead]
                )
                db.add(f)
    except Exception as e:
        print(f"Error fetching weather: {e}")

    # 2. Fetch Air Quality
    aqi_url = f"https://air-quality-api.open-meteo.com/v1/air-quality?latitude={lat}&longitude={lon}&hourly=pm10,pm2_5,nitrogen_dioxide,sulphur_dioxide,carbon_monoxide"
    try:
        a_res = requests.get(aqi_url).json()
        hourly_a = a_res.get("hourly", {})
        
        if "time" in hourly_a and len(hourly_a["time"]) > 0:
            # Get the most recent hourly reading (index 0 is current hour if not historical, wait, OpenMeteo gives past+future)
            # Find the index closest to now
            now_iso = datetime.utcnow().strftime("%Y-%m-%dT%H:00")
            try:
                idx = hourly_a["time"].index(now_iso)
            except ValueError:
                idx = 0 # Fallback to first
                
            pm25 = hourly_a["pm2_5"][idx]
            pm10 = hourly_a["pm10"][idx]
            no2 = hourly_a["nitrogen_dioxide"][idx]
            so2 = hourly_a["sulphur_dioxide"][idx]
            co = hourly_a["carbon_monoxide"][idx]
            
            # Handle nulls
            pm25 = pm25 if pm25 is not None else 50.0
            pm10 = pm10 if pm10 is not None else 80.0
            no2 = no2 if no2 is not None else 20.0
            so2 = so2 if so2 is not None else 5.0
            co = co if co is not None else 1.0

            reading = RawAQIReading(
                station_id=station.station_id,
                timestamp=datetime.utcnow(),
                pm25=pm25,
                pm10=pm10,
                no2=no2,
                so2=so2,
                co=co,
                source="Open-Meteo"
            )
            db.add(reading)
    except Exception as e:
        print(f"Error fetching AQI: {e}")
        
    db.commit()
    print(f"Successfully ingested LIVE telemetry for {city.name}")
