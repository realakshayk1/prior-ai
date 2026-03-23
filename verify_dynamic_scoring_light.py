import sys
import os
import json
import datetime
print("Starting verification script...")
from catboost import CatBoostClassifier, Pool

RISK_MODEL_PATH = "model.cbm"
_risk_model = None

def score_clinical_risk_standalone(patient_data: dict, procedure_code: str = "missing") -> dict:
    global _risk_model
    try:
        if not os.path.exists(RISK_MODEL_PATH):
            return {"error": "Risk model model.cbm not found.", "tool": "score_clinical_risk"}
        
        if _risk_model is None:
            _risk_model = CatBoostClassifier()
            _risk_model.load_model(RISK_MODEL_PATH)
        
        fallbacks = {}
        
        # Extract features
        age = 50
        if patient_data.get('birthDate'):
            try:
                year = int(patient_data['birthDate'].split('-')[0])
                age = 2026 - year # Using current local year 2026 from user metadata
            except:
                fallbacks['age'] = "defaulted to 50"
        
        gender_val = patient_data.get('gender')
        gender = '1' if gender_val == 'male' else '2'
        
        conditions = patient_data.get('conditions', [])
        primary_dx = conditions[0]['code'] if conditions else 'missing'
        comorbidity_count = max(0, len(conditions) - 1)
        
        # DYNAMIC FEATURES FIXED HERE
        proc_code = procedure_code
        procedures = patient_data.get('procedures', [])
        claims_list = patient_data.get('claims', [])
        num_prior_claims = len(procedures) + len(claims_list)
        
        if num_prior_claims == 0:
            fallbacks['num_prior_claims'] = "defaulted to 0 — no prior procedures found in FHIR"
        
        features = [age, gender, primary_dx, proc_code, comorbidity_count, num_prior_claims]
        
        # Predict
        probs = _risk_model.predict_proba([features])[0]
        denial_prob = float(probs[1])
        
        result = {
            "features_used": {
                "age": age,
                "gender": gender,
                "primary_dx": primary_dx,
                "proc_code": proc_code,
                "comorbidity_count": comorbidity_count,
                "num_prior_claims": num_prior_claims
            },
            "denial_probability": denial_prob,
            "risk_tier": "high" if denial_prob > 0.7 else ("medium" if denial_prob > 0.4 else "low")
        }
        if fallbacks: result["feature_fallback"] = fallbacks
        return result
    except Exception as e:
        return {"error": str(e)}

def extract_from_synthea(file_path):
    with open(file_path, 'r') as f:
        bundle = json.load(f)
    
    patient = None
    conditions, procedures, claims = [], [], []
    
    for entry in bundle.get("entry", []):
        resource = entry.get("resource", {})
        rt = resource.get("resourceType")
        if rt == "Patient": patient = resource
        elif rt == "Condition": conditions.append({"code": resource.get("code", {}).get("coding", [{}])[0].get("code")})
        elif rt == "Procedure": procedures.append({"code": resource.get("code", {}).get("coding", [{}])[0].get("code")})
        elif rt == "Claim": claims.append({"id": resource.get("id")})
            
    return {
        "patient_id": patient.get("id"),
        "birthDate": patient.get("birthDate"),
        "gender": patient.get("gender"),
        "conditions": conditions,
        "procedures": procedures,
        "claims": claims
    }

def test_dynamic_scoring():
    # 1. Test Patient with rich history
    p1_path = "synthea_output/fhir/Carey440_Osinski784_2947070c-c37c-45e6-8d32-3d5decb1e5db.json"
    p1_data = extract_from_synthea(p1_path)
    print(f"--- Patient 1: {p1_data['patient_id']} ---")
    res1 = score_clinical_risk_standalone(p1_data, procedure_code="HCPCS_RICH")
    print(json.dumps(res1, indent=2))

    # 2. Test Patient with potentially sparse history
    p2_path = "synthea_output/fhir/Abby752_Desire394_Waters156_0dc8682d-2843-5fa5-a5e8-66bb3209ec37.json"
    p2_data = extract_from_synthea(p2_path)
    print(f"\n--- Patient 2: {p2_data['patient_id']} ---")
    res2 = score_clinical_risk_standalone(p2_data, procedure_code="HCPCS_SPARSE")
    print(json.dumps(res2, indent=2))

if __name__ == "__main__":
    test_dynamic_scoring()
