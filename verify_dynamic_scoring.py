import sys
import os
import json

# Add current directory to path
sys.path.append(os.getcwd())

from run_agent import score_clinical_risk

def extract_from_synthea(file_path):
    with open(file_path, 'r') as f:
        bundle = json.load(f)
    
    patient = None
    conditions = []
    procedures = []
    claims = []
    
    for entry in bundle.get("entry", []):
        resource = entry.get("resource", {})
        rt = resource.get("resourceType")
        if rt == "Patient":
            patient = resource
        elif rt == "Condition":
            conditions.append({
                "code": resource.get("code", {}).get("coding", [{}])[0].get("code"),
                "display": resource.get("code", {}).get("coding", [{}])[0].get("display")
            })
        elif rt == "Procedure":
            procedures.append({
                "code": resource.get("code", {}).get("coding", [{}])[0].get("code"),
                "display": resource.get("code", {}).get("coding", [{}])[0].get("display")
            })
        elif rt == "Claim":
            claims.append({
                "id": resource.get("id"),
                "status": resource.get("status")
            })
            
    # Mock the fhir_tool output structure
    context = {
        "patient_id": patient.get("id"),
        "birthDate": patient.get("birthDate"),
        "gender": patient.get("gender"),
        "conditions": conditions,
        "procedures": procedures,
        "claims": claims
    }
    return context

def test_dynamic_scoring():
    # 1. Test Patient with rich history
    p1_path = "synthea_output/fhir/Carey440_Osinski784_2947070c-c37c-45e6-8d32-3d5decb1e5db.json"
    p1_data = extract_from_synthea(p1_path)
    
    print(f"--- Testing Patient 1: {p1_data['patient_id']} ---")
    print(f"History: {len(p1_data['procedures'])} procedures, {len(p1_data['claims'])} claims")
    
    res1 = score_clinical_risk(p1_data, procedure_code="HCPCS_A")
    print(f"Result (Risk Tier): {res1['risk_tier']}")
    # Verify SHAP factors/fallbacks
    print(f"Top Factors: {res1['shap_top_factors']}")
    if 'feature_fallback' in res1:
        print(f"Fallbacks: {json.dumps(res1['feature_fallback'], indent=2)}")
    else:
        print("No fallbacks (correct - rich history)")

    # 2. Test Patient with potentially sparse history
    p2_path = "synthea_output/fhir/Abby752_Desire394_Waters156_0dc8682d-2843-5fa5-a5e8-66bb3209ec37.json"
    p2_data = extract_from_synthea(p2_path)
    
    print(f"\n--- Testing Patient 2: {p2_data['patient_id']} ---")
    print(f"History: {len(p2_data['procedures'])} procedures, {len(p2_data['claims'])} claims")
    
    res2 = score_clinical_risk(p2_data, procedure_code="HCPCS_B")
    print(f"Result (Risk Tier): {res2['risk_tier']}")
    print(f"Top Factors: {res2['shap_top_factors']}")
    if 'feature_fallback' in res2:
        print(f"Fallbacks: {json.dumps(res2['feature_fallback'], indent=2)}")
    
    # 3. Test patient with 0 services (forcing fallback)
    p3_data = p2_data.copy()
    p3_data['procedures'] = []
    p3_data['claims'] = []
    
    print(f"\n--- Testing Forced Fallback (Patient 3) ---")
    res3 = score_clinical_risk(p3_data, procedure_code="HCPCS_FALLBACK")
    print(f"Fallbacks: {json.dumps(res3.get('feature_fallback', {}), indent=2)}")

if __name__ == "__main__":
    test_dynamic_scoring()
