import json
import os

ICD10_FILE = "icd10_codes.json"
CRITERIA_FILE = "criteria.json"

def load_json(file_path):
    if not os.path.exists(file_path):
        return {}
    with open(file_path, 'r') as f:
        return json.load(f)

def validate_icd10_codes(code_list: list) -> dict:
    """
    Validates a list of ICD-10 codes against a local JSON dataset.
    Returns a dictionary with valid and invalid codes.
    """
    icd_data = load_json(ICD10_FILE)
    results = {"valid": [], "invalid": []}
    
    for code in code_list:
        if code in icd_data:
            results["valid"].append({"code": code, "description": icd_data[code]})
        else:
            results["invalid"].append(code)
            
    return results

def check_auth_criteria(dx_code: str, procedure_name: str) -> dict:
    """
    Checks if a diagnosis and procedure meet medical necessity criteria.
    """
    criteria = load_json(CRITERIA_FILE)
    
    # Check if diagnosis exists in criteria
    if dx_code in criteria:
        required_procedure = criteria[dx_code]
        # Case-insensitive match for procedure name
        if procedure_name.lower() in required_procedure.lower():
            return {
                "match": True,
                "diagnosis": dx_code,
                "procedure": procedure_name,
                "message": "Criteria met for prior authorization."
            }
        else:
            return {
                "match": False,
                "diagnosis": dx_code,
                "procedure": procedure_name,
                "required": required_procedure,
                "message": f"Criteria mismatch. Required procedure: {required_procedure}"
            }
            
    return {
        "match": False,
        "diagnosis": dx_code,
        "message": "Diagnosis code not found in criteria dataset."
    }

if __name__ == "__main__":
    import sys
    
    # Simple test
    print("Testing validate_icd10_codes(['I10', 'Z99.9']):")
    print(json.dumps(validate_icd10_codes(["I10", "Z99.9"]), indent=2))
    
    print("\nTesting check_auth_criteria('I82.409', 'Venous Duplex Scan'):")
    print(json.dumps(check_auth_criteria("I82.409", "Venous Duplex Scan"), indent=2))
