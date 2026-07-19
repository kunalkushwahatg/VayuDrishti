import requests
from datetime import datetime
from src.db.session import SessionLocal
from src.db.models import City, RawWeather

def fetch_weather_for_city(city: City, db):
    # Open-Meteo URL (using dummy lat/lon for testing if city doesn't have it, but let's assume New Delhi)
    # Since city model only has state/name, we will hardcode coordinates for MVP testing or add lat/lon to City.
    # For MVP, we'll map city names to coordinates.
    coords = {
        "Delhi": (28.6139, 77.2090),
        "Mumbai": (19.0760, 72.8777)
    }
    lat, lon = coords.get(city.name, (28.6139, 77.2090)) # default to Delhi
    
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true&hourly=temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,wind_direction_10m"
    
    print(f"Fetching weather for {city.name}...")
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        current = data.get("current_weather", {})
        hourly = data.get("hourly", {})
        
        # Insert Current Weather
        weather = RawWeather(
            city_id=city.city_id,
            timestamp=datetime.utcnow(),
            wind_speed=current.get("windspeed"),
            wind_dir=current.get("winddirection"),
            temp=current.get("temperature"),
            humidity=0.0, # not in current_weather
            precipitation=0.0
        )
        db.add(weather)
        
        # Insert Future Forecasts (+24h, +48h, +72h)
        # OpenMeteo hourly arrays map 1:1 with hours. Index 24 = roughly 24 hours from start.
        if "time" in hourly and len(hourly["time"]) >= 73:
            for hours_ahead in [24, 48, 72]:
                dt = datetime.fromisoformat(hourly["time"][hours_ahead])
                forecast = RawWeather(
                    city_id=city.city_id,
                    timestamp=dt,
                    wind_speed=hourly["wind_speed_10m"][hours_ahead],
                    wind_dir=hourly["wind_direction_10m"][hours_ahead],
                    temp=hourly["temperature_2m"][hours_ahead],
                    humidity=hourly["relative_humidity_2m"][hours_ahead],
                    precipitation=hourly["precipitation"][hours_ahead]
                )
                db.add(forecast)
                print(f"Added {hours_ahead}h forecast for {city.name} at {dt}")
        
        db.commit()
        print(f"Successfully inserted current and forecasted weather data for {city.name}.")
    else:
        print(f"Failed to fetch weather: {response.status_code}")

def run():
    db = SessionLocal()
    # Ensure at least one city exists for testing
    delhi = db.query(City).filter_by(name="Delhi").first()
    if not delhi:
        delhi = City(name="Delhi", state="Delhi", timezone="Asia/Kolkata")
        db.add(delhi)
        db.commit()
        db.refresh(delhi)
    
    fetch_weather_for_city(delhi, db)
    db.close()

if __name__ == "__main__":
    run()
