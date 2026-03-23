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

def check_auth_criteria(dx_code, procedure_name: str) -> dict:
    """
    Checks if a diagnosis and procedure meet medical necessity criteria.
    Accepts dx_code as a single string or a list of strings.
    """
    criteria = load_json(CRITERIA_FILE)
    
    # Handle list of diagnosis codes
    dx_codes = dx_code if isinstance(dx_code, list) else [dx_code]
    
    criteria_met_count = 0
    total_criteria_count = 0
    matched_dx = []
    
    for dx in dx_codes:
        # Check if diagnosis exists in criteria
        if dx in criteria:
            total_criteria_count += 1
            required_procedure = criteria[dx]
            
            # More flexible match: check if procedure name contains the criteria word or vice-versa
            required_words = [w for w in required_procedure.lower().replace('(', '').replace(')', '').split() if len(w) > 3]
            provided_words = procedure_name.lower().split()
            
            # Match if any significant word from criteria is in provided procedure name
            match_found = False
            for word in required_words:
                if word in procedure_name.lower():
                    match_found = True
                    break
            
            # Additional fallback check for first word match (e.g. CPT code)
            if not match_found and provided_words:
                if provided_words[0] in required_procedure.lower():
                    match_found = True
            
            if match_found:
                criteria_met_count += 1
                matched_dx.append(dx)
            
    # Return match: True if any match, but also include counts for programmatic confidence
    return {
        "match": criteria_met_count > 0,
        "criteria_met_count": criteria_met_count,
        "total_criteria_count": total_criteria_count,
        "matched_diagnoses": matched_dx,
        "diagnosis": dx_codes,
        "procedure": procedure_name,
        "message": "Criteria met for prior authorization." if criteria_met_count > 0 else "Criteria mismatch or diagnosis not found in criteria dataset."
    }

if __name__ == "__main__":
    import sys
    
    # Simple test
    print("Testing validate_icd10_codes(['I10', 'Z99.9']):")
    print(json.dumps(validate_icd10_codes(["I10", "Z99.9"]), indent=2))
    
    print("\nTesting check_auth_criteria('I82.409', 'Venous Duplex Scan'):")
    print(json.dumps(check_auth_criteria("I82.409", "Venous Duplex Scan"), indent=2))
