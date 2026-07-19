import json
import sys
from datetime import datetime
sys.stdout.reconfigure(encoding='utf-8')

from src.db.session import SessionLocal
from src.db.models import City, Ward, AttributionResult, ForecastGrid, EnforcementWorklist, Anomaly, QueryLog
from src.llm.wrapper import get_llm

def gather_context_from_db(db, city_id):
    """Pulls the latest intelligence from all other agents into a single JSON evidence bundle."""
    context = {}
    
    # 1. Agent 1: Attribution
    ward = db.query(Ward).filter_by(city_id=city_id).first()
    if ward:
        attribution = db.query(AttributionResult).filter_by(ward_id=ward.ward_id).order_by(AttributionResult.timestamp.desc()).first()
        if attribution:
            context["Agent1_Attribution"] = {
                "vehicles_contribution": f"{attribution.pct_vehicular}%",
                "construction_contribution": f"{attribution.pct_construction}%",
                "industrial_contribution": f"{attribution.pct_industrial}%",
                "confidence_score": f"{attribution.confidence_score}"
            }
        
    # 2. Agent 2: Forecast (Just taking +24h for the first ward as an example)
    ward = db.query(Ward).filter_by(city_id=city_id).first()
    if ward:
        forecast = db.query(ForecastGrid).filter_by(city_id=city_id, horizon_hours=24).order_by(ForecastGrid.forecast_made_at.desc()).first()
        if forecast:
            context["Agent2_Forecast"] = {
                "ward": ward.name,
                "predicted_aqi_tomorrow": forecast.aqi_predicted
            }
            
    # 3. Agent 3: Enforcement Priority
    enforcement = db.query(EnforcementWorklist).filter_by(ward_id=ward.ward_id).order_by(EnforcementWorklist.priority_score.desc()).first()
    if enforcement:
        context["Agent3_Enforcement_Priority"] = {
            "target_site_id": enforcement.site_id,
            "priority_score": enforcement.priority_score,
            "justification": enforcement.justification_text
        }
        
    # 4. Agent 6: Anomalies
    anomaly = db.query(Anomaly).filter_by(ward_id=ward.ward_id).order_by(Anomaly.timestamp.desc()).first()
    if anomaly:
         context["Agent6_Recent_Anomalies"] = {
             "z_score": anomaly.z_score,
             "investigation_note": anomaly.investigation_note
         }
         
    return context

def construct_llm_prompt(question, evidence_bundle):
    """Instructs the LLM to answer the question using ONLY the provided database evidence."""
    system_prompt = """You are VayuDrishti's Chief Intelligence Officer.
You are answering a question from a city administrator about urban air quality.

CRITICAL RULES:
1. You MUST answer the user's question using ONLY the data provided in the <evidence_bundle>.
2. Do not hallucinate or use outside knowledge. 
3. Explicitly cite your sources by naming the Agent (e.g., "According to Agent 1's Source Attribution...").
4. If the evidence bundle does not contain the answer, say "I do not have the data to answer this question."
"""

    user_prompt = f"""
<evidence_bundle>
{json.dumps(evidence_bundle, indent=2)}
</evidence_bundle>

USER QUESTION: "{question}"
"""
    return system_prompt, user_prompt

def run_agent_7(test_question: str):
    print(f"Starting Agent 7: Natural Language Query Agent")
    print(f"User Question: '{test_question}'\n")
    db = SessionLocal()
    
    delhi = db.query(City).filter_by(name="Delhi").first()
    if not delhi:
        print("Delhi not found in database.")
        return
        
    # 1. RAG Retrieval
    print("Fetching latest intelligence from Agents 1, 2, 3, and 6...")
    evidence_bundle = gather_context_from_db(db, delhi.city_id)
    
    # 2. Synthesis
    print("Calling Groq LLM API to synthesize answer...")
    system_prompt, user_prompt = construct_llm_prompt(test_question, evidence_bundle)
    
    llm = get_llm(provider="groq")
    answer = llm.generate_text(
        prompt=user_prompt,
        system_prompt=system_prompt,
        temperature=0.1
    )
    
    print("\n=== AGENT 7 ANSWER ===")
    print(answer)
    print("======================\n")
    
    # 3. Persist
    log = QueryLog(
        user_id="test_admin_01",
        question=test_question,
        city_id=delhi.city_id,
        final_answer=answer,
        tools_called_json=json.dumps(list(evidence_bundle.keys())),
        timestamp=datetime.utcnow()
    )
    db.add(log)
    db.commit()
    print("Saved query to query_log table.")
    
    db.close()

if __name__ == "__main__":
    q = "Give me a summary of Delhi's current air quality situation, the main cause, and the top place we should send inspectors."
    run_agent_7(q)
