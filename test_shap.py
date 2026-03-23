import sys
import os
import json

# Add current directory to path
sys.path.append(os.getcwd())

from run_agent import score_clinical_risk

def test():
    # Mock patient data
    patient_data = {
        "birthDate": "1970-01-01",
        "gender": "male",
        "conditions": [
            {"code": "I10", "display": "Essential (primary) hypertension"},
            {"code": "E11", "display": "Type 2 diabetes mellitus"}
        ]
    }
    
    print("Testing score_clinical_risk with dynamic SHAP factors...")
    result = score_clinical_risk(patient_data)
    
    print(json.dumps(result, indent=2))
    
    if "shap_top_factors" in result:
        print("\nSUCCESS: Dynamic SHAP factors found.")
        print(f"Top factors: {result['shap_top_factors']}")
    else:
        print("\nFAILURE: SHAP factors missing.")

if __name__ == "__main__":
    test()
