import random
from datetime import datetime, timedelta
from src.db.session import SessionLocal
from src.db.models import City, Ward, Station, RawAQIReading, AttributionResult, Intervention

def setup_agent4_mock():
    print("Setting up dummy data for Agent 4 (Comparative Dashboard)...")
    db = SessionLocal()
    
    # 1. Setup Mumbai
    mumbai = db.query(City).filter_by(name="Mumbai").first()
    if not mumbai:
        mumbai = City(name="Mumbai", state="Maharashtra", timezone="Asia/Kolkata")
        db.add(mumbai)
        db.commit()
        
    mumbai_ward = db.query(Ward).filter_by(name="Bandra Kurla Complex").first()
    if not mumbai_ward:
        mumbai_ward = Ward(city_id=mumbai.city_id, name="Bandra Kurla Complex", boundary_geojson="{}")
        db.add(mumbai_ward)
        db.commit()
        
    mumbai_station = db.query(Station).filter_by(ward_id=mumbai_ward.ward_id).first()
    if not mumbai_station:
        mumbai_station = Station(ward_id=mumbai_ward.ward_id, name="BKC CAAQMS", lat=19.0664, lon=72.8658, source="CPCB")
        db.add(mumbai_station)
        db.commit()

    delhi = db.query(City).filter_by(name="Delhi").first()
    delhi_ward = db.query(Ward).filter_by(city_id=delhi.city_id).first()
    delhi_station = db.query(Station).filter_by(ward_id=delhi_ward.ward_id).first()
    
    if not delhi:
        print("Delhi not found. Run Agent 1 first.")
        return

    # 2. Setup Historical AQI (30 days) and Interventions
    now = datetime.utcnow()
    intervention_date = now - timedelta(days=15)
    
    # Check if we already inserted this
    existing = db.query(Intervention).filter_by(policy_name="Odd-Even Vehicle Ban").first()
    if not existing:
        policy = Intervention(
            city_id=delhi.city_id,
            ward_id=delhi_ward.ward_id,
            policy_name="Odd-Even Vehicle Ban",
            start_date=intervention_date,
            logged_by="Delhi Transport Dept"
        )
        db.add(policy)
        
        # Insert 30 days of data
        for i in range(30):
            day = now - timedelta(days=i)
            
            # Delhi Data
            # Before intervention (i >= 15): AQI ~ 300
            # After intervention (i < 15): AQI ~ 240 (20% drop)
            delhi_aqi = random.uniform(280, 320) if i >= 15 else random.uniform(230, 250)
            
            delhi_reading = RawAQIReading(
                station_id=delhi_station.station_id,
                timestamp=day,
                pm25=delhi_aqi * 0.6,
                pm10=delhi_aqi * 1.2,
                no2=delhi_aqi * 0.4,
                so2=10.0,
                co=1.5,
                source="MOCK_HISTORICAL"
            )
            db.add(delhi_reading)
            
            delhi_attr = AttributionResult(
                ward_id=delhi_ward.ward_id,
                timestamp=day,
                pct_vehicular=70.0,
                pct_construction=10.0,
                pct_industrial=10.0,
                pct_burning=5.0,
                pct_dust=5.0,
                confidence_score=0.8,
                signals_available_json="[]"
            )
            db.add(delhi_attr)
            
            # Mumbai Data
            # Mumbai is flat around AQI 150
            mumbai_aqi = random.uniform(140, 160)
            mumbai_reading = RawAQIReading(
                station_id=mumbai_station.station_id,
                timestamp=day,
                pm25=mumbai_aqi * 0.6,
                pm10=mumbai_aqi * 1.2,
                no2=mumbai_aqi * 0.1,
                so2=mumbai_aqi * 0.8, # high SO2
                co=0.5,
                source="MOCK_HISTORICAL"
            )
            db.add(mumbai_reading)
            
            mumbai_attr = AttributionResult(
                ward_id=mumbai_ward.ward_id,
                timestamp=day,
                pct_vehicular=15.0,
                pct_construction=10.0,
                pct_industrial=65.0, # High Industrial
                pct_burning=0.0,
                pct_dust=10.0,
                confidence_score=0.7,
                signals_available_json="[]"
            )
            db.add(mumbai_attr)
            
        db.commit()
        print("Mock historical data and Odd-Even intervention inserted successfully.")
    else:
        print("Mock data already exists.")
        
    db.close()

if __name__ == "__main__":
    setup_agent4_mock()
