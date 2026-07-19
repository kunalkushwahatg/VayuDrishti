from datetime import datetime, timedelta
from src.db.session import SessionLocal
from src.db.models import City, Ward, Station, RawAQIReading

def setup_agent6_mock():
    print("Setting up dummy data for Agent 6 (Anomaly Investigation)...")
    db = SessionLocal()
    
    delhi = db.query(City).filter_by(name="Delhi").first()
    delhi_ward = db.query(Ward).filter_by(city_id=delhi.city_id).first()
    delhi_station = db.query(Station).filter_by(ward_id=delhi_ward.ward_id).first()
    
    if not delhi:
        print("Delhi not found. Run Agent 1 first.")
        return

    # Insert a massive spike right now
    now = datetime.utcnow()
    
    spike_reading = RawAQIReading(
        station_id=delhi_station.station_id,
        timestamp=now,
        pm25=450.0, # Massive spike (AQI > 500)
        pm10=500.0,
        no2=80.0,
        so2=10.0,
        co=2.5,
        source="MOCK_ANOMALY"
    )
    db.add(spike_reading)
    db.commit()
    
    print(f"Inserted massive AQI spike at {now} for {delhi.name}.")
    db.close()

if __name__ == "__main__":
    setup_agent6_mock()
