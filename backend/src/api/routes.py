from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from pydantic import BaseModel

from src.db.session import SessionLocal
from src.db.models import City, Ward, ForecastGrid, AttributionResult, EnforcementWorklist, Advisory, Anomaly, QueryLog
from src.agents.agent7_nl_query import gather_context_from_db, construct_llm_prompt
from src.agents.agent1_attribution import run_agent_1
from src.agents.agent2_forecast import run_agent_2
from src.agents.agent3_enforcement import run_agent_3
from src.agents.agent6_anomaly import run_agent_6
from src.agents.agent5_advisory import run_agent_5
from src.ingestion.live_telemetry import fetch_live_telemetry
from src.llm.wrapper import get_llm
import json
from datetime import datetime

router = APIRouter()

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/forecasts", response_model=List[Dict[str, Any]])
def get_forecasts(city_name: str = "Delhi", db: Session = Depends(get_db)):
    city = db.query(City).filter_by(name=city_name).first()
    if not city:
        raise HTTPException(status_code=404, detail="City not found")
        
    forecasts = db.query(ForecastGrid).filter_by(city_id=city.city_id, horizon_hours=24).order_by(ForecastGrid.forecast_made_at.desc()).limit(10).all()
    return [{"ward_id": f.grid_cell_id, "aqi": f.aqi_predicted, "timestamp": f.forecast_made_at} for f in forecasts]

@router.get("/attribution", response_model=Dict[str, Any])
def get_attribution(city_name: str = "Delhi", db: Session = Depends(get_db)):
    city = db.query(City).filter_by(name=city_name).first()
    ward = db.query(Ward).filter_by(city_id=city.city_id).first()
    
    attr = db.query(AttributionResult).filter_by(ward_id=ward.ward_id).order_by(AttributionResult.timestamp.desc()).first()
    if not attr:
        return {}
    return {
        "vehicles": attr.pct_vehicular,
        "dust": attr.pct_dust,
        "industry": attr.pct_industrial,
        "burning": attr.pct_burning,
        "confidence": attr.confidence_score
    }

@router.get("/enforcement", response_model=List[Dict[str, Any]])
def get_enforcement(city_name: str = "Delhi", db: Session = Depends(get_db)):
    from src.db.models import EmissionSite
    city = db.query(City).filter_by(name=city_name).first()
    ward = db.query(Ward).filter_by(city_id=city.city_id).first()
    
    items = db.query(EnforcementWorklist).filter_by(ward_id=ward.ward_id).order_by(EnforcementWorklist.date.desc(), EnforcementWorklist.priority_score.desc()).limit(15).all()
    results = []
    seen_sites = set()
    for i in items:
        site = db.query(EmissionSite).filter_by(site_id=i.site_id).first()
        site_name = site.permit_ref if site else str(i.site_id)
        if site_name in seen_sites:
            continue
        seen_sites.add(site_name)
        lat = site.lat if site else 0.0
        lon = site.lon if site else 0.0
        results.append({"site_id": i.site_id, "site_name": site_name, "lat": lat, "lon": lon, "score": i.priority_score, "justification": i.justification_text})
        if len(results) >= 5:
            break
    return results

@router.get("/anomalies", response_model=List[Dict[str, Any]])
def get_anomalies(city_name: str = "Delhi", db: Session = Depends(get_db)):
    city = db.query(City).filter_by(name=city_name).first()
    ward = db.query(Ward).filter_by(city_id=city.city_id).first()
    
    items = db.query(Anomaly).filter_by(ward_id=ward.ward_id).order_by(Anomaly.timestamp.desc()).limit(5).all()
    return [{"timestamp": i.timestamp, "z_score": i.z_score, "report": i.investigation_note} for i in items]

@router.get("/advisories", response_model=List[Dict[str, Any]])
def get_advisories(city_name: str = "Delhi", db: Session = Depends(get_db)):
    city = db.query(City).filter_by(name=city_name).first()
    ward = db.query(Ward).filter_by(city_id=city.city_id).first()
    
    items = db.query(Advisory).filter_by(ward_id=ward.ward_id).order_by(Advisory.generated_at.desc()).limit(3).all()
    return [{"channel": i.channel, "language": i.language, "text": i.text} for i in items]

class QueryRequest(BaseModel):
    question: str
    city_name: str = "Delhi"

@router.post("/ask")
def ask_agent7(req: QueryRequest, db: Session = Depends(get_db)):
    city = db.query(City).filter_by(name=req.city_name).first()
    if not city:
        raise HTTPException(status_code=404, detail="City not found")
        
    evidence_bundle = gather_context_from_db(db, city.city_id)
    system_prompt, user_prompt = construct_llm_prompt(req.question, evidence_bundle)
    
    llm = get_llm(provider="groq")
    answer = llm.generate_text(prompt=user_prompt, system_prompt=system_prompt, temperature=0.1)
    
    log = QueryLog(
        user_id="api_user",
        question=req.question,
        city_id=city.city_id,
        final_answer=answer,
        tools_called_json=json.dumps(list(evidence_bundle.keys())),
        timestamp=datetime.utcnow()
    )
    db.add(log)
    db.commit()
    
    return {"answer": answer}

class LocationRequest(BaseModel):
    name: str
    lat: float
    lon: float

@router.post("/locations")
def initialize_location(req: LocationRequest, db: Session = Depends(get_db)):
    print(f"Initializing location: {req.name} ({req.lat}, {req.lon})")
    
    # 1. Create City and Ward if they don't exist
    city = db.query(City).filter_by(name=req.name).first()
    if not city:
        city = City(name=req.name, state="Unknown", timezone="Asia/Kolkata")
        db.add(city)
        db.commit()
        
    ward = db.query(Ward).filter_by(city_id=city.city_id, name=req.name).first()
    if not ward or not ward.boundary_geojson or ward.boundary_geojson == "{}":
        # Fetch OSM boundary
        geojson_str = "{}"
        try:
            def fetch_poly(params):
                import requests
                res = requests.get("https://nominatim.openstreetmap.org/search", params=params, headers={'User-Agent': 'VayuDrishti/1.0'}).json()
                if res and "features" in res:
                    for feat in res["features"]:
                        if feat.get("geometry", {}).get("type") in ["Polygon", "MultiPolygon"]:
                            return json.dumps(feat)
                return None
                
            # Try 1: Exact city
            poly = fetch_poly({"city": req.name, "format": "geojson", "polygon_geojson": 1, "limit": 5})
            if not poly:
                # Try 2: Municipal Corporation
                poly = fetch_poly({"q": f"{req.name} Municipal Corporation", "format": "geojson", "polygon_geojson": 1, "limit": 5})
            
            if poly:
                geojson_str = poly
            else:
                # Universal fallback: Create a 10x10km bounding box around the coordinates
                offset = 0.05 # roughly 5.5km
                lat, lon = req.lat, req.lon
                box_feature = {
                    "type": "Feature",
                    "properties": {"name": f"{req.name} Approximate Area"},
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[
                            [lon - offset, lat - offset],
                            [lon + offset, lat - offset],
                            [lon + offset, lat + offset],
                            [lon - offset, lat + offset],
                            [lon - offset, lat - offset]
                        ]]
                    }
                }
                geojson_str = json.dumps(box_feature)
        except Exception as e:
            print(f"Failed to fetch borders for {req.name}: {e}")
            
        if not ward:
            ward = Ward(city_id=city.city_id, name=req.name, boundary_geojson=geojson_str)
            db.add(ward)
        else:
            ward.boundary_geojson = geojson_str
        db.commit()
        
    ward_id = ward.ward_id
    
    # 2. Fetch Live Telemetry
    try:
        fetch_live_telemetry(db, city, ward, req.lat, req.lon)
    except Exception as e:
        print(f"Telemetry failed: {e}")
        
    # 3. Run Agents Pipeline
    try:
        run_agent_1(ward_id)
        run_agent_2(ward_id)
        run_agent_3(ward_id)
        run_agent_6(ward_id)
        run_agent_5(ward_id)
    except Exception as e:
        print(f"Agent pipeline failed: {e}")
        
    return {"status": "success", "city": city.name, "ward_id": ward_id}

@router.get("/current_aqi", response_model=Dict[str, Any])
def get_current_aqi(city_name: str = "Delhi", db: Session = Depends(get_db)):
    from src.ingestion.aqi_calculator import calculate_indian_aqi
    from src.db.models import Station, RawAQIReading
    
    city = db.query(City).filter_by(name=city_name).first()
    if not city:
        return {"aqi": 220, "dominant_pollutant": "PM2.5"} # Fallback
        
    ward = db.query(Ward).filter_by(city_id=city.city_id).first()
    if not ward:
        return {"aqi": 220, "dominant_pollutant": "PM2.5"}
        
    station = db.query(Station).filter_by(ward_id=ward.ward_id).first()
    if not station:
        return {"aqi": 220, "dominant_pollutant": "PM2.5"}
        
    reading = db.query(RawAQIReading).filter_by(station_id=station.station_id).order_by(RawAQIReading.timestamp.desc()).first()
    if not reading:
        return {"aqi": 220, "dominant_pollutant": "PM2.5"}
        
    co_mg_m3 = reading.co / 1000.0 if reading.co else 0
    aqi_val, dom_pol = calculate_indian_aqi(reading.pm25, reading.pm10, reading.no2, reading.so2, co_mg_m3)
    return {"aqi": aqi_val, "dominant_pollutant": dom_pol}

@router.get("/boundary", response_model=Dict[str, Any])
def get_boundary(city_name: str = "Delhi", db: Session = Depends(get_db)):
    city = db.query(City).filter_by(name=city_name).first()
    if not city:
        return {"geojson": None}
    ward = db.query(Ward).filter_by(city_id=city.city_id).first()
    if not ward or not ward.boundary_geojson or ward.boundary_geojson == "{}":
        return {"geojson": None}
    
    import json
    try:
        return {"geojson": json.loads(ward.boundary_geojson)}
    except:
        return {"geojson": None}
