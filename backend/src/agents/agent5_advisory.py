import sys
sys.stdout.reconfigure(encoding='utf-8')
from datetime import datetime
from src.db.session import SessionLocal
from src.db.models import City, Ward, ForecastGrid, Advisory
from src.llm.wrapper import get_llm

# Maps a city to its dominant regional language for citizen advisories.
# The PS explicitly asks for Bengaluru→Kannada, Chennai→Tamil, etc.
CITY_LANGUAGE_MAP = {
    "Bengaluru": "Kannada",
    "Bangalore": "Kannada",
    "Chennai": "Tamil",
    "Mumbai": "Marathi",
    "Kolkata": "Bengali",
    "Hyderabad": "Telugu",
    "Ahmedabad": "Gujarati",
    "Pune": "Marathi",
    "Delhi": "Hindi",
    "New Delhi": "Hindi",
}

def get_regional_language(city_name: str) -> str:
    """Returns the dominant regional language for a city, defaulting to Hindi."""
    return CITY_LANGUAGE_MAP.get(city_name, "Hindi")

def get_cpcb_tier(aqi: float):
    """Deterministic, rule-based mapping of AQI to health tier based on Indian CPCB standards."""
    if aqi <= 50:
        return "Good", "Air quality is good. Minimal health impact."
    elif aqi <= 100:
        return "Satisfactory", "Air quality is satisfactory. Minor breathing discomfort to sensitive people."
    elif aqi <= 200:
        return "Moderate", "Air quality is moderate. Breathing discomfort to people with lungs, asthma and heart diseases."
    elif aqi <= 300:
        return "Poor", "Air quality is poor. Breathing discomfort to most people on prolonged exposure."
    elif aqi <= 400:
        return "Very Poor", "Air quality is very poor. Respiratory illness on prolonged exposure."
    else:
        return "Severe", "Air quality is severe. Affects healthy people and seriously impacts those with existing diseases."

def construct_llm_prompt(base_template, channel, language):
    """Instructs the LLM to format/translate the template WITHOUT adding new medical claims."""
    
    system_prompt = f"""You are a Public Health Communication Formatter. 
Your only job is to adapt the provided medical warning into the target format and language.

CRITICAL RULES:
1. Do NOT invent or add any new medical advice.
2. Only translate/format the exact meaning of the original template.
"""

    if channel == "push":
        system_prompt += f"\nFORMAT RULE: Output MUST be in {language}. Must be punchy and under 150 characters (SMS format)."
    elif channel == "ivr":
        system_prompt += f"\nFORMAT RULE: Output MUST be in {language}. Must be a conversational script designed to be read aloud by an automated phone system to an elderly person. Start with 'Hello, this is a health alert from VayuDrishti'."
    elif channel == "display":
        system_prompt += f"\nFORMAT RULE: Output MUST be in {language}. Must be exactly 3 to 5 words max, suitable for reading on a highway digital billboard at 80km/h."

    user_prompt = f"""
Please adapt this official health warning:
"{base_template}"
"""
    return system_prompt, user_prompt

def run_agent_5(ward_id: int):
    print(f"Starting Agent 5 for Ward ID: {ward_id}")
    db = SessionLocal()
    
    # 1. Load Agent 2 Forecast Data
    ward = db.query(Ward).filter_by(ward_id=ward_id).first()
    if not ward:
        return
        
    city = db.query(City).filter_by(city_id=ward.city_id).first()
        
    forecast = db.query(ForecastGrid).filter_by(city_id=city.city_id, horizon_hours=24).order_by(ForecastGrid.forecast_made_at.desc()).first()
    
    if not forecast:
        print("Forecast data not found. Run Agent 2 first.")
        return
        
    aqi = forecast.aqi_predicted
    print(f"Loaded 24h Forecast for {city.name}: AQI {aqi:.1f}")
    
    # 2. Rule-Based Categorization
    tier, base_template = get_cpcb_tier(aqi)
    print(f"Categorized as Tier: {tier}")
    print(f"Official CPCB Template: '{base_template}'")
    
    # 3. LLM Formatting & Translation — advisories go out in the city's regional language.
    regional_lang = get_regional_language(city.name)
    print(f"Regional language for {city.name}: {regional_lang}")
    channels = [
        {"name": "push", "lang": regional_lang},   # SMS/app push in the local language
        {"name": "ivr", "lang": regional_lang},     # phone script for elderly, local language
        {"name": "display", "lang": "English"}      # highway billboards kept in English
    ]

    llm = get_llm(provider="groq")

    print("\nCalling Groq LLM API for Formatting/Translation...")
    
    for c in channels:
        system_prompt, user_prompt = construct_llm_prompt(base_template, c["name"], c["lang"])
        
        localized_text = llm.generate_text(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.1 # Low temp to prevent hallucination
        )
        
        print(f"\n--- {c['name'].upper()} ({c['lang']}) ---")
        print(localized_text)
        
        # 4. Persist
        advisory = Advisory(
            ward_id=ward.ward_id,
            tier=tier,
            channel=c["name"],
            language=c["lang"],
            text=localized_text,
            generated_at=datetime.utcnow()
        )
        db.add(advisory)
        
    db.commit()
    print("\nSuccessfully saved all advisories to database.")
    db.close()

if __name__ == "__main__":
    import sys
    ward_id = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    run_agent_5(ward_id)
