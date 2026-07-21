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
    telemetry = {"aqi_ok": False, "weather_ok": False, "error": "not attempted"}
    try:
        telemetry = fetch_live_telemetry(db, city, ward, req.lat, req.lon)
    except Exception as e:
        telemetry = {"aqi_ok": False, "weather_ok": False, "error": str(e)}
        print(f"Telemetry failed: {e}")

    # 3. Run Agents Pipeline — only if we actually got fresh AQI data, so we
    # don't regenerate attributions/advisories off stale numbers.
    if telemetry.get("aqi_ok"):
        try:
            run_agent_1(ward_id)
            run_agent_2(ward_id)
            run_agent_3(ward_id)
            run_agent_6(ward_id)
            run_agent_5(ward_id)
        except Exception as e:
            print(f"Agent pipeline failed: {e}")
    else:
        print(f"Skipping agent pipeline for {city.name}: no fresh AQI data.")

    return {
        "status": "success" if telemetry.get("aqi_ok") else "no_live_data",
        "city": city.name,
        "ward_id": ward_id,
        "live_data": telemetry.get("aqi_ok", False),
        "detail": telemetry.get("error"),
    }

# A reading older than this is considered stale, not "live".
AQI_FRESHNESS_HOURS = 3

@router.get("/current_aqi", response_model=Dict[str, Any])
def get_current_aqi(city_name: str = "Delhi", db: Session = Depends(get_db)):
    from src.ingestion.aqi_calculator import calculate_indian_aqi
    from src.db.models import Station, RawAQIReading
    from datetime import timedelta

    def no_data(reason):
        # Explicit "no data" instead of a fake 220 that looks like a real reading.
        return {"aqi": None, "dominant_pollutant": None, "stale": True, "no_data": True, "reason": reason}

    city = db.query(City).filter_by(name=city_name).first()
    if not city:
        return no_data("city not found")

    ward = db.query(Ward).filter_by(city_id=city.city_id).first()
    if not ward:
        return no_data("no ward")

    station = db.query(Station).filter_by(ward_id=ward.ward_id).first()
    if not station:
        return no_data("no station")

    reading = db.query(RawAQIReading).filter_by(station_id=station.station_id).order_by(RawAQIReading.timestamp.desc()).first()
    if not reading:
        return no_data("no readings")

    co_mg_m3 = reading.co / 1000.0 if reading.co else 0
    aqi_val, dom_pol = calculate_indian_aqi(reading.pm25, reading.pm10, reading.no2, reading.so2, co_mg_m3)

    # Freshness guard: flag (don't hide) data older than the threshold so the UI
    # can show "as of <time>" instead of presenting past data as live.
    age = datetime.utcnow() - reading.timestamp if reading.timestamp else None
    is_stale = age is not None and age > timedelta(hours=AQI_FRESHNESS_HOURS)
    return {
        "aqi": aqi_val,
        "dominant_pollutant": dom_pol,
        "as_of": reading.timestamp,
        "stale": is_stale,
        "no_data": False,
    }

@router.get("/forecast_accuracy", response_model=Dict[str, Any])
def get_forecast_accuracy(city_name: str = "Delhi", horizon: int = 24, db: Session = Depends(get_db)):
    """Model RMSE vs. persistence baseline, evaluated on real backfilled history.
    Cached in forecast_accuracy_log; re-computed at most once per hour per city."""
    from src.db.models import Station, ForecastAccuracyLog
    from src.ingestion.forecast_accuracy import evaluate_forecast_skill
    from datetime import timedelta

    city = db.query(City).filter_by(name=city_name).first()
    if not city:
        raise HTTPException(status_code=404, detail="City not found")

    # Serve a cached result if we scored this city/horizon within the last hour
    cached = db.query(ForecastAccuracyLog).filter_by(city_id=city.city_id, horizon_hours=horizon).order_by(ForecastAccuracyLog.date.desc()).first()
    if cached and cached.date and (datetime.utcnow() - cached.date) < timedelta(hours=1):
        rmse_m, rmse_p = cached.rmse_model, cached.rmse_persistence
        imp = ((rmse_p - rmse_m) / rmse_p * 100.0) if rmse_p else 0.0
        return {"city": city_name, "horizon_hours": horizon, "rmse_model": rmse_m,
                "rmse_persistence": rmse_p, "improvement_pct": round(imp, 1),
                "beats_baseline": rmse_m < rmse_p, "cached": True}

    # Resolve coordinates from a station in the city (fallback to Delhi centre)
    ward = db.query(Ward).filter_by(city_id=city.city_id).first()
    station = db.query(Station).filter_by(ward_id=ward.ward_id).first() if ward else None
    lat = station.lat if station and station.lat else 28.6139
    lon = station.lon if station and station.lon else 77.2090

    try:
        result = evaluate_forecast_skill(lat, lon, horizon_hours=horizon)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Could not evaluate forecast skill: {e}")

    db.add(ForecastAccuracyLog(city_id=city.city_id, horizon_hours=horizon,
                               date=datetime.utcnow(), rmse_model=result["rmse_model"],
                               rmse_persistence=result["rmse_persistence"]))
    db.commit()

    result["city"] = city_name
    result["cached"] = False
    return result

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
