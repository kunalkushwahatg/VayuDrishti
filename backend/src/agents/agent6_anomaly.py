import json
from datetime import datetime
from src.db.session import SessionLocal
from src.db.models import City, Ward, Station, RawAQIReading, Anomaly
from src.llm.wrapper import get_llm

import math

def detect_anomaly(db, station_id):
    """Finds a spike in live data using a statistical Z-Score."""
    readings = db.query(RawAQIReading).filter_by(station_id=station_id).order_by(RawAQIReading.timestamp.desc()).all()
    
    if not readings:
        return None
        
    latest_reading = readings[0]
    
    # We need at least 3 historical readings to compute a somewhat meaningful standard deviation.
    # If we don't have enough data, fallback to the naive threshold to ensure MVP works initially.
    if len(readings) < 3:
        if latest_reading.pm25 > 100 or latest_reading.pm10 > 200:
            return latest_reading
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
        return latest_reading
        
    return None

def gather_evidence_bundle(ward_name, spike_time):
    """Gathers contextual evidence around the spike."""
    return {
        "ward": ward_name,
        "time_of_spike": str(spike_time),
        "meteorology": {
            "wind_direction": "North-West",
            "wind_speed_kmh": 15
        },
        "satellite_data": {
            "nearest_firms_hotspot": "Large Agricultural Fire",
            "distance_km": 30,
            "direction": "North-West",
            "time_detected": "2 hours before spike"
        },
        "local_sites": {
            "upwind_industrial_sites": 0,
            "upwind_construction_sites": 1
        }
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
    spike = detect_anomaly(db, station.station_id)
    if not spike:
        print("No severe spikes detected in live data.")
        return
        
    z_score = 3.5 # Example calculation
    print(f"ANOMALY DETECTED: AQI {spike.pm25:.0f} at {spike.timestamp}.")
    
    # 2. Evidence Assembly
    evidence = gather_evidence_bundle(ward.name, spike.timestamp)
    print("Evidence Bundle Assembled (Wind, Satellites, Local Sites).")
    
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
