import json
import random
from datetime import datetime, timedelta
from src.db.session import SessionLocal
from src.db.models import City, RawWeather, RawAQIReading, ForecastGrid, Station, Ward

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
        
    current_aqi_val = (latest_aqi.pm25 + latest_aqi.pm10) / 2 # rough mock
    print(f"Current Baseline AQI: {current_aqi_val:.1f}")
    
    for horizon in [24, 48, 72]:
        future_weather = get_future_weather(db, city.city_id, horizon)
        
        if not future_weather:
            print(f"No future weather found for {horizon}h. Skipping.")
            continue
            
        print(f"\n--- {horizon}h Forecast ---")
        print(f"Predicted Weather -> Wind: {future_weather.wind_speed} km/h, Temp: {future_weather.temp} C")
        
        # Statistical / Physics Drift
        # 1. High wind disperses pollution (lowers AQI)
        # 2. Low temperature causes thermal inversion (traps pollution, raises AQI)
        wind_effect = future_weather.wind_speed * -2.5
        temp_effect = (35.0 - future_weather.temp) * 1.5 
        
        drift = wind_effect + temp_effect
        predicted_aqi = max(20.0, current_aqi_val + drift)
        
        # Uncertainty band grows with time (e.g. 10% at 24h, 20% at 48h, 30% at 72h)
        uncertainty = predicted_aqi * (0.05 + (horizon / 240.0)) 
        
        print(f"Predicted AQI: {predicted_aqi:.1f} ±{uncertainty:.1f}")
        
        # Persist to DB
        forecast = ForecastGrid(
            city_id=city.city_id,
            grid_cell_id="DEL-1", # mock 1km grid
            forecast_made_at=datetime.utcnow(),
            horizon_hours=horizon,
            aqi_predicted=predicted_aqi,
            uncertainty_band=uncertainty,
            physics_component=drift,
            ml_component=0.0 # MVP statistical mode
        )
        db.add(forecast)
        
    db.commit()
    print("\nSuccessfully wrote Agent 2 forecast results to the database.")
    db.close()

if __name__ == "__main__":
    import sys
    ward_id = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    run_agent_2(ward_id)
