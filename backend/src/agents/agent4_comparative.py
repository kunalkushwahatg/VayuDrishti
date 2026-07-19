import json
from datetime import datetime, timedelta
from src.db.session import SessionLocal
from src.db.models import City, Ward, Station, RawAQIReading, AttributionResult, Intervention, InterventionEffect
from src.llm.wrapper import get_llm
# pyrefly: ignore [missing-import]
from sqlalchemy import func

def calculate_did_effect(db, intervention, station_id):
    """Calculates the Difference-in-Differences effect size (simplified MVP)"""
    start = intervention.start_date
    
    # Avg AQI Before (days -30 to -15)
    before_avg = db.query(func.avg(RawAQIReading.pm25)).filter(
        RawAQIReading.station_id == station_id,
        RawAQIReading.timestamp < start
    ).scalar() or 1.0
    
    # Avg AQI After (days -15 to now)
    after_avg = db.query(func.avg(RawAQIReading.pm25)).filter(
        RawAQIReading.station_id == station_id,
        RawAQIReading.timestamp >= start
    ).scalar() or 1.0
    
    # Simplistic effect size calculation (percentage change)
    effect_size = ((after_avg - before_avg) / before_avg) * 100.0
    return effect_size

def construct_llm_prompt(policy_name, source_city_name, source_effect, source_mix, target_city_name, target_mix):
    """Constructs the prompt for the transferability reasoning."""
    system_prompt = """You are a Senior Environmental Policy Advisor. 
Your job is to read data about a policy's effectiveness in City A, and advise if it should be implemented in City B based on their distinct pollution profiles.

CRITICAL RULES:
1. Write EXACTLY 3 sentences. No conversational filler.
2. You MUST cite the specific pollution breakdown percentages of BOTH cities to justify your reasoning.
3. Explicitly state whether the policy is "RECOMMENDED" or "NOT RECOMMENDED" for the target city.
4. Rely ONLY on the data provided in the <data> tags. Do not hallucinate.
"""

    data_payload = {
        "policy": policy_name,
        "source_city": {
            "name": source_city_name,
            "effect_observed": f"{source_effect:.1f}% change in AQI",
            "pollution_mix": source_mix
        },
        "target_city": {
            "name": target_city_name,
            "pollution_mix": target_mix
        }
    }

    user_prompt = f"""
Please evaluate transferability based on this data:
<data>
{json.dumps(data_payload, indent=2)}
</data>
"""
    return system_prompt, user_prompt

def run_agent_4():
    print("Starting Agent 4: Multi-City Comparative Intelligence Dashboard")
    db = SessionLocal()
    
    # 1. Load Intervention
    intervention = db.query(Intervention).filter_by(policy_name="Odd-Even Vehicle Ban").first()
    if not intervention:
        print("Intervention not found. Run setup_agent4_mock.py first.")
        return
        
    delhi = db.query(City).filter_by(city_id=intervention.city_id).first()
    delhi_station = db.query(Station).filter_by(ward_id=intervention.ward_id).first()
    
    # 2. Calculate Effect
    effect_size = calculate_did_effect(db, intervention, delhi_station.station_id)
    print(f"Calculated Effect in {delhi.name}: {effect_size:.1f}% AQI change.")
    
    # 3. Load Target City (Mumbai)
    mumbai = db.query(City).filter_by(name="Mumbai").first()
    mumbai_ward = db.query(Ward).filter_by(city_id=mumbai.city_id).first()
    
    # 4. Load Pollution Mixes (Agent 1 Output)
    delhi_attr = db.query(AttributionResult).filter_by(ward_id=intervention.ward_id).order_by(AttributionResult.timestamp.desc()).first()
    mumbai_attr = db.query(AttributionResult).filter_by(ward_id=mumbai_ward.ward_id).order_by(AttributionResult.timestamp.desc()).first()
    
    delhi_mix = {"vehicular": f"{delhi_attr.pct_vehicular}%", "industrial": f"{delhi_attr.pct_industrial}%"}
    mumbai_mix = {"vehicular": f"{mumbai_attr.pct_vehicular}%", "industrial": f"{mumbai_attr.pct_industrial}%"}
    
    # 5. LLM Transferability Check
    print(f"Calling Groq LLM API to evaluate transferability from {delhi.name} to {mumbai.name}...")
    system_prompt, user_prompt = construct_llm_prompt(
        intervention.policy_name, delhi.name, effect_size, delhi_mix, mumbai.name, mumbai_mix
    )
    
    llm = get_llm(provider="groq")
    transferability_note = llm.generate_text(
        prompt=user_prompt,
        system_prompt=system_prompt,
        temperature=0.1
    )
    
    print("\n=== LLM POLICY ADVISORY ===")
    print(transferability_note)
    print("===========================\n")
    
    # 6. Persist
    effect = InterventionEffect(
        intervention_id=intervention.intervention_id,
        effect_size=effect_size,
        confidence_interval_low=effect_size - 2.0, # dummy CI
        confidence_interval_high=effect_size + 2.0, # dummy CI
        transferability_note=transferability_note,
        target_city_id=mumbai.city_id
    )
    db.add(effect)
    db.commit()
    print("Successfully saved Intervention Effect to database.")
    
    db.close()

if __name__ == "__main__":
    run_agent_4()
