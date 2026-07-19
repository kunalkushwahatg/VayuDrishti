import json
from datetime import datetime
from src.db.session import SessionLocal
from src.db.models import City, Ward, Station, RawAQIReading, RawWeather, RawFireHotspot, EmissionSite, Anomaly
from src.llm.wrapper import get_llm
from src.ingestion.firms_satellite import fetch_firms_hotspots, is_upwind, deg_to_compass

import math

def detect_anomaly(db, station_id):
    """Finds a spike in live data using a statistical Z-Score.

    Returns a tuple (reading, z_score) or None if no anomaly.
    """
    readings = db.query(RawAQIReading).filter_by(station_id=station_id).order_by(RawAQIReading.timestamp.desc()).all()

    if not readings:
        return None

    latest_reading = readings[0]

    # We need at least 3 historical readings to compute a somewhat meaningful standard deviation.
    # If we don't have enough data, fallback to the naive threshold to ensure MVP works initially.
    if len(readings) < 3:
        if latest_reading.pm25 > 100 or latest_reading.pm10 > 200:
            return (latest_reading, 2.5)  # nominal z-score for threshold trigger
        return None

    # 1. Calculate Mean of PM2.5
    pm25_values = [r.pm25 for r in readings if r.pm25 is not None]
    if not pm25_values:
        return None

    mean_pm25 = sum(pm25_values) / len(pm25_values)

    # 2. Calculate Standard Deviation
    variance = sum((x - mean_pm25) ** 2 for x in pm25_values) / len(pm25_values)
    std_dev_pm25 = math.sqrt(variance)

    # Avoid division by zero if all historical readings are exactly identical
    if std_dev_pm25 == 0:
        std_dev_pm25 = 1.0

    # 3. Calculate Z-Score
    z_score = (latest_reading.pm25 - mean_pm25) / std_dev_pm25

    # If the Z-Score is > 2.0 (Meaning the current reading is 2 standard deviations above normal)
    if z_score > 2.0:
        print(f"Statistical Anomaly Detected! Z-Score: {z_score:.2f} (Mean: {mean_pm25:.1f}, StdDev: {std_dev_pm25:.1f}, Current: {latest_reading.pm25})")
        return (latest_reading, round(z_score, 2))

    return None

def gather_evidence_bundle(db, ward, station, spike_time):
    """Gathers REAL contextual evidence around the spike:
    - live meteorology from the DB (Open-Meteo)
    - real NASA FIRMS active-fire satellite detections near the station
    - registered emission sites in the ward
    Falls back to conservative estimates only when live signals are unavailable.
    """
    city = db.query(City).filter_by(city_id=ward.city_id).first()

    # --- 1. Real meteorology from the latest ingested weather ---
    weather = db.query(RawWeather).filter_by(city_id=ward.city_id).order_by(RawWeather.timestamp.desc()).first()
    if weather:
        wind_dir_deg = weather.wind_dir
        wind_dir_label = deg_to_compass(weather.wind_dir)
        wind_speed = weather.wind_speed
        met_source = "Open-Meteo (live)"
    else:
        wind_dir_deg, wind_dir_label, wind_speed, met_source = None, "Unknown", None, "unavailable"

    # --- 2. Real satellite: NASA FIRMS active fires near the station ---
    fires = fetch_firms_hotspots(station.lat, station.lon, radius_deg=1.5, day_range=1) if station else []

    if fires:
        nearest = fires[0]
        # Persist all detected hotspots for the map / audit trail
        for f in fires[:20]:
            try:
                acq = datetime.strptime(f["acq_date"], "%Y-%m-%d") if f.get("acq_date") else spike_time
            except ValueError:
                acq = spike_time
            db.add(RawFireHotspot(lat=f["lat"], lon=f["lon"], timestamp=acq,
                                  frp=f["frp"], source="VIIRS_SNPP_NRT"))
        db.commit()

        upwind = is_upwind(nearest["direction"], wind_dir_deg)
        satellite_block = {
            "source": "NASA FIRMS VIIRS S-NPP (375m, real)",
            "active_fires_detected": len(fires),
            "nearest_hotspot_distance_km": nearest["distance_km"],
            "nearest_hotspot_direction": nearest["direction"],
            "nearest_hotspot_frp_mw": nearest["frp"],
            "hotspot_is_upwind": upwind,
            "acq_date": nearest.get("acq_date", ""),
        }
    else:
        satellite_block = {
            "source": "NASA FIRMS (no active fires detected or key unavailable)",
            "active_fires_detected": 0,
            "note": "No thermal anomalies found in a ~150km radius in the last 24h.",
        }

    # --- 3. Real registered emission sites in the ward ---
    industrial = db.query(EmissionSite).filter_by(ward_id=ward.ward_id, type="industrial").count()
    construction = db.query(EmissionSite).filter_by(ward_id=ward.ward_id, type="construction").count()

    return {
        "ward": ward.name,
        "city": city.name if city else "Unknown",
        "time_of_spike": str(spike_time),
        "meteorology": {
            "wind_direction": wind_dir_label,
            "wind_speed": wind_speed,
            "source": met_source,
        },
        "satellite_data": satellite_block,
        "local_sites": {
            "registered_industrial_sites": industrial,
            "registered_construction_sites": construction,
        },
    }

def construct_llm_prompt(evidence_bundle):
    """Instructs the LLM to reason over the evidence and explicitly state uncertainty."""
    
    system_prompt = """You are the Lead Environmental Anomaly Investigator. 
Your job is to read an evidence bundle describing a sudden spike in air pollution and explain the likely cause.

CRITICAL RULES:
1. Reason through the physics explicitly (e.g., check if the wind direction and speed align with the distance to the fire and the time delay).
2. Write a formal 3-4 sentence investigation report.
3. You MUST end your report with a "CONFIDENCE:" statement (High, Moderate, or Low).
4. You MUST end your report with an "UNCERTAINTY:" statement explicitly stating what evidence is missing or cannot be proven.
5. Do not hallucinate data. Rely only on the <evidence> tags.
"""

    user_prompt = f"""
Please investigate this anomaly based on the following evidence bundle:
<evidence>
{json.dumps(evidence_bundle, indent=2)}
</evidence>
"""
    return system_prompt, user_prompt

def run_agent_6(ward_id: int):
    print(f"Starting Agent 6 for Ward ID: {ward_id}")
    db = SessionLocal()
    
    ward = db.query(Ward).filter_by(ward_id=ward_id).first()
    if not ward:
        return
        
    station = db.query(Station).filter_by(ward_id=ward.ward_id).first()
    if not station:
        return
    
    # 1. Trigger / Math Check
    result = detect_anomaly(db, station.station_id)
    if not result:
        print("No severe spikes detected in live data.")
        return

    spike, z_score = result
    print(f"ANOMALY DETECTED: PM2.5 {spike.pm25:.0f} at {spike.timestamp} (z-score {z_score}).")

    # 2. Evidence Assembly (real weather + NASA FIRMS satellite + registered sites)
    evidence = gather_evidence_bundle(db, ward, station, spike.timestamp)
    print("Evidence Bundle Assembled (Live Wind, NASA FIRMS Satellite, Local Sites).")
    
    # 3. LLM Reasoning
    print("\nCalling Groq LLM API to investigate...")
    system_prompt, user_prompt = construct_llm_prompt(evidence)
    
    llm = get_llm(provider="groq")
    report = llm.generate_text(
        prompt=user_prompt,
        system_prompt=system_prompt,
        temperature=0.2 # Slight temperature to allow reasoning
    )
    
    print("\n=== INVESTIGATION REPORT ===")
    print(report)
    print("============================\n")
    
    # 4. Persist
    anomaly = Anomaly(
        ward_id=ward.ward_id,
        timestamp=spike.timestamp,
        z_score=z_score,
        investigation_note=report,
        evidence_json=json.dumps(evidence),
        confidence_statement="See report", # MVP shortcut
        human_reviewed=False
    )
    db.add(anomaly)
    db.commit()
    
    print("Successfully saved anomaly investigation to database.")
    db.close()

if __name__ == "__main__":
    import sys
    ward_id = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    run_agent_6(ward_id)
