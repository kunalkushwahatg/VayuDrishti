import json
import random
from datetime import datetime
from src.db.session import SessionLocal
from src.db.models import City, Ward, Station, RawWeather, RawAQIReading, AttributionResult

def run_agent_1(ward_id: int):
    print(f"Starting Agent 1 for Ward ID: {ward_id}")
    db = SessionLocal()
    
    ward = db.query(Ward).filter_by(ward_id=ward_id).first()
    if not ward:
        print("Ward not found.")
        return
        
    city = db.query(City).filter_by(city_id=ward.city_id).first()
    station = db.query(Station).filter_by(ward_id=ward.ward_id).first()
    
    if not station:
        print("No station found for this ward. Run live telemetry ingestion first.")
        return
    
    # 1. Fetch latest raw data
    latest_aqi = db.query(RawAQIReading).filter_by(station_id=station.station_id).order_by(RawAQIReading.timestamp.desc()).first()
    if not latest_aqi:
        print("No AQI data found. Run live telemetry ingestion first.")
        return
        
    latest_weather = db.query(RawWeather).filter_by(city_id=city.city_id).order_by(RawWeather.timestamp.desc()).first()
    
    import math
    
    # 2. Heuristics (Chemical Fingerprinting & Ratios)
    # Unit normalization: OpenMeteo gives all in ug/m3.
    # To prevent division by zero, we use max(value, 0.1)
    pm25 = max(latest_aqi.pm25, 0.1)
    pm10 = max(latest_aqi.pm10, 0.1)
    no2 = max(latest_aqi.no2, 0.1)
    so2 = max(latest_aqi.so2, 0.1)
    co = max(latest_aqi.co, 0.1) # CO is typically very large (1000-5000)

    # Calculate raw heuristic affinities
    # 1. Vehicular: High NOx, moderate CO. Proxy: NO2 / PM2.5
    raw_vehicular = (no2 / pm25) * 1.5 
    
    # 2. Industrial: High SO2 relative to NO2. Proxy: SO2 / NO2
    raw_industrial = (so2 / no2) * 2.0
    
    # 3. Biomass Burning: Exceptionally high CO. Proxy: CO / (NO2 * 100)
    raw_burning = (co / (no2 * 100.0)) * 1.0
    
    # 4. Dust/Construction: Coarse particles. Proxy: (PM10 - PM2.5) / PM10
    coarse_fraction = (pm10 - pm25) / pm10
    raw_dust = max(coarse_fraction, 0.0) * 4.0

    # 3. Meteorological Dispersion Penalty
    signals_available = ["live_api", "heuristic_algo"]
    confidence = 0.85
    
    if latest_weather:
        signals_available.append("wind_weather")
        confidence += 0.05
        wind_speed = latest_weather.wind_speed if latest_weather.wind_speed is not None else 0.0
        
        # High wind disperses local gases but kicks up dust
        if wind_speed > 5.0: # m/s roughly
            raw_vehicular *= 0.7
            raw_industrial *= 0.8
            raw_burning *= 0.6
            raw_dust *= 1.5
        # Low wind traps emissions
        elif wind_speed < 1.5:
            raw_vehicular *= 1.3
            raw_industrial *= 1.2
            raw_burning *= 1.4
            raw_dust *= 0.7
            
    # Softmax Normalization for robust probability distribution
    # Add temperature scaling to control sharpness
    temperature = 1.2
    
    scores = [raw_vehicular, raw_industrial, raw_burning, raw_dust]
    exp_scores = [math.exp(min(s / temperature, 20.0)) for s in scores] # Clamp to prevent overflow
    sum_exp = sum(exp_scores)
    
    pct_vehicular = (exp_scores[0] / sum_exp) * 100
    pct_industrial = (exp_scores[1] / sum_exp) * 100
    pct_burning = (exp_scores[2] / sum_exp) * 100
    pct_dust = (exp_scores[3] / sum_exp) * 100
    
    print(f"\n--- Attribution Results for {ward.name} ---")
    print(f"Vehicular: {pct_vehicular:.1f}%")
    print(f"Industrial: {pct_industrial:.1f}%")
    print(f"Dust/Construction: {pct_dust:.1f}%")
    print(f"Biomass Burning: {pct_burning:.1f}%")
    print(f"Confidence: {confidence:.2f}")
    
    result = AttributionResult(
        ward_id=ward.ward_id,
        timestamp=datetime.utcnow(),
        pct_vehicular=pct_vehicular,
        pct_construction=0.0, 
        pct_industrial=pct_industrial,
        pct_burning=pct_burning,
        pct_dust=pct_dust,
        confidence_score=confidence,
        signals_available_json=json.dumps(signals_available)
    )
    db.add(result)
    db.commit()
    db.close()

if __name__ == "__main__":
    import sys
    ward_id = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    run_agent_1(ward_id)
