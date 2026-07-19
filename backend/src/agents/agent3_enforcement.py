import json
import random
from datetime import datetime
from src.db.session import SessionLocal
from src.db.models import City, Ward, EmissionSite, Inspector, AttributionResult, ForecastGrid, EnforcementWorklist
from src.llm.wrapper import get_llm
import requests

def fetch_osm_sites(city_name: str, target_type: str = "construction") -> list:
    print(f"Fetching real {target_type} sites in {city_name} from OpenStreetMap...")
    if target_type == "construction":
        tags = 'way["landuse"="construction"]'
    else:
        tags = 'way["landuse"="industrial"](area.searchArea); way["man_made"="works"]'
        
    query = f"""
    [out:json];
    area[name="{city_name}"]->.searchArea;
    (
      {tags}(area.searchArea);
    );
    out center 5;
    """
    
    try:
        res = requests.get("http://overpass-api.de/api/interpreter", params={"data": query}, headers={'User-Agent': 'VayuDrishti/1.0'}, timeout=10)
        data = res.json()
        sites = []
        for el in data.get("elements", []):
            lat = el.get("center", {}).get("lat", 0)
            lon = el.get("center", {}).get("lon", 0)
            name = el.get("tags", {}).get("name", "")
            if not name:
                name = f"OSM-ID-{el.get('id')}"
            sites.append({
                "name": name,
                "lat": lat,
                "lon": lon,
                "type": target_type
            })
        return sites
    except Exception as e:
        print(f"OSM fetch failed: {e}")
        return []

def get_or_create_inspector(db, city):
    inspector = db.query(Inspector).filter_by(city_id=city.city_id).first()
    if not inspector:
        inspector = Inspector(city_id=city.city_id, name="Rajesh Kumar", base_lat=28.6, base_lon=77.2, daily_capacity=3)
        db.add(inspector)
        db.commit()
    return inspector

def construct_llm_prompt(site, attribution, forecast):
    """Constructs an industry-grade, injection-resistant prompt."""
    
    system_prompt = """You are the Senior Environmental Enforcement Supervisor for VayuDrishti. 
Your job is to read raw telemetry data and write a strict, professional 3-sentence justification instructing a field inspector on why they must inspect a specific site today.

CRITICAL RULES:
1. Output EXACTLY 3 sentences. No more, no less.
2. Use a commanding, professional tone.
3. You MUST cite the specific PM2.5/PM10 percentages and 24h forecasted AQI from the data.
4. DO NOT hallucinate facts. DO NOT add conversational filler (e.g., do not say "Here is the justification:").
5. Rely ONLY on the data provided in the <evidence> tags.
"""

    evidence_data = {
        "site_type": site.type,
        "permit_ref": site.permit_ref,
        "ward_dust_contribution_pct": round(attribution.pct_dust + attribution.pct_construction, 1),
        "forecast_24h_aqi": round(forecast.aqi_predicted, 1),
        "forecast_trend": "worsening" if forecast.physics_component > 0 else "improving"
    }

    user_prompt = f"""
Please generate the inspection justification based on this data:
<evidence>
{json.dumps(evidence_data, indent=2)}
</evidence>
"""
    return system_prompt, user_prompt

def run_agent_3(ward_id: int):
    print(f"Starting Agent 3 for Ward ID: {ward_id}")
    db = SessionLocal()
    
    ward = db.query(Ward).filter_by(ward_id=ward_id).first()
    if not ward:
        return
    city = db.query(City).filter_by(city_id=ward.city_id).first()
    
    inspector = get_or_create_inspector(db, city)
    
    # 1. Fetch Agent 1 and Agent 2 data
    attribution = db.query(AttributionResult).filter_by(ward_id=ward.ward_id).order_by(AttributionResult.timestamp.desc()).first()
    forecast = db.query(ForecastGrid).filter_by(city_id=city.city_id, horizon_hours=24).order_by(ForecastGrid.forecast_made_at.desc()).first()
    
    if not attribution or not forecast:
        print("Missing Attribution (Agent 1) or Forecast (Agent 2) data. Run them first.")
        return
        
    print(f"Loaded Agent 1 (Dust: {attribution.pct_dust}%, Industry: {attribution.pct_industrial}%) and Agent 2 (24h AQI: {forecast.aqi_predicted})")
    
    # Fetch real OSM sites based on priority
    target_type = "construction" if attribution.pct_dust >= attribution.pct_industrial else "industrial"
    osm_sites = fetch_osm_sites(city.name, target_type)
    
    if osm_sites:
        # Pick one random site from the top 5 returned by OSM
        chosen_osm = random.choice(osm_sites)
        site = EmissionSite(ward_id=ward.ward_id, type=chosen_osm["type"], lat=chosen_osm["lat"], lon=chosen_osm["lon"], permit_ref=chosen_osm["name"])
        db.add(site)
        db.commit()
    else:
        print("No real sites fetched from OSM. Skipping enforcement assignment to avoid dummy data.")
        db.close()
        return
    
    # 2. Math Scoring
    impact = (attribution.pct_dust + attribution.pct_construction) * 1.5
    if forecast.physics_component > 0: impact *= 1.2 # Worsening forecast penalty
    
    feasibility = 0.9 # Hardcoded MVP
    priority = (impact * 0.6) + (feasibility * 0.4)
    
    # 3. LLM Reasoning
    print("\nCalling Groq LLM API for justification generation...")
    system_prompt, user_prompt = construct_llm_prompt(site, attribution, forecast)
    
    llm = get_llm(provider="groq")
    justification = llm.generate_text(
        prompt=user_prompt,
        system_prompt=system_prompt,
        temperature=0.1 # Very low temp for strict deterministic output
    )
    
    print("\n=== LLM OUTPUT ===")
    print(justification)
    print("==================\n")
    
    # 4. Persist
    worklist = EnforcementWorklist(
        ward_id=ward.ward_id,
        site_id=site.site_id,
        date=datetime.utcnow(),
        priority_score=priority,
        impact_score=impact,
        feasibility_score=feasibility,
        assigned_inspector_id=inspector.inspector_id,
        justification_text=justification,
        evidence_json=json.dumps({"attribution_id": attribution.id, "forecast_id": forecast.id}),
        status="pending"
    )
    db.add(worklist)
    db.commit()
    print("Successfully saved enforcement assignment to database.")
    
    db.close()

if __name__ == "__main__":
    import sys
    ward_id = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    run_agent_3(ward_id)
