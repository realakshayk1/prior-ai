import requests

FHIR_BASE = "http://localhost:8080/fhir/"

def fetch_patient_context(patient_id: str) -> dict:
    """
    Queries HAPI FHIR for Patient demographics, Conditions, 
    MedicationRequests, and Observations for a given patient ID.
    Returns a normalized dictionary.
    """
    try:
        # 1. Fetch Patient
        resp = requests.get(f"{FHIR_BASE}Patient/{patient_id}")
        if resp.status_code != 200:
            return {"error": f"Patient {patient_id} not found (Status {resp.status_code})"}
        patient = resp.json()
        
        # 2. Fetch Conditions
        resp = requests.get(f"{FHIR_BASE}Condition?patient={patient_id}&_count=50")
        conditions = [
            {
                "code": c.get("resource", {}).get("code", {}).get("coding", [{}])[0].get("code"),
                "display": c.get("resource", {}).get("code", {}).get("coding", [{}])[0].get("display"),
                "status": c.get("resource", {}).get("clinicalStatus", {}).get("coding", [{}])[0].get("code")
            }
            for c in resp.json().get("entry", [])
        ]
        
        # 3. Fetch MedicationRequests
        resp = requests.get(f"{FHIR_BASE}MedicationRequest?patient={patient_id}&_count=50")
        medications = [
            {
                "display": m.get("resource", {}).get("medicationCodeableConcept", {}).get("coding", [{}])[0].get("display"),
                "status": m.get("resource", {}).get("status"),
                "authoredOn": m.get("resource", {}).get("authoredOn")
            }
            for m in resp.json().get("entry", [])
        ]
        
        # 4. Fetch Observations (Labs/Vitals)
        resp = requests.get(f"{FHIR_BASE}Observation?patient={patient_id}&_count=50")
        observations = [
            {
                "display": o.get("resource", {}).get("code", {}).get("coding", [{}])[0].get("display"),
                "value": o.get("resource", {}).get("valueQuantity", {}).get("value"),
                "unit": o.get("resource", {}).get("valueQuantity", {}).get("unit"),
                "effectiveDateTime": o.get("resource", {}).get("effectiveDateTime")
            }
            for o in resp.json().get("entry", [])
        ]

        # 5. Fetch Procedures (for prior history)
        resp = requests.get(f"{FHIR_BASE}Procedure?patient={patient_id}&_count=50")
        procedures = [
            {
                "code": p.get("resource", {}).get("code", {}).get("coding", [{}])[0].get("code"),
                "display": p.get("resource", {}).get("code", {}).get("coding", [{}])[0].get("display"),
                "status": p.get("resource", {}).get("status")
            }
            for p in resp.json().get("entry", [])
        ]

        # 6. Fetch Claims (for prior history)
        resp = requests.get(f"{FHIR_BASE}Claim?patient={patient_id}&_count=50")
        claims = [
            {
                "id": c.get("resource", {}).get("id"),
                "type": c.get("resource", {}).get("type", {}).get("coding", [{}])[0].get("code"),
                "status": c.get("resource", {}).get("status")
            }
            for c in resp.json().get("entry", [])
        ]

        # 7. Fetch Coverage (for insurance validation)
        resp = requests.get(f"{FHIR_BASE}Coverage?patient={patient_id}&_count=10")
        coverage = [
            {
                "payor": c.get("resource", {}).get("payor", [{}])[0].get("display"),
                "coverage_status": c.get("resource", {}).get("status"),
                "coverage_class": c.get("resource", {}).get("class", [{}])[0].get("value") if c.get("resource", {}).get("class") else None
            }
            for c in resp.json().get("entry", [])
        ]
        
        # Normalization
        context = {
            "patient_id": patient_id,
            "name": " ".join(patient.get("name", [{}])[0].get("given", [])) + " " + patient.get("name", [{}])[0].get("family", ""),
            "gender": patient.get("gender"),
            "birthDate": patient.get("birthDate"),
            "conditions": conditions,
            "medications": medications,
            "observations": observations,
            "procedures": procedures,
            "claims": claims,
            "coverage": coverage
        }
        return context
        
    except Exception as e:
        return {"error": f"Failed to fetch context: {str(e)}"}

if __name__ == "__main__":
    import json
    import sys
    
    # Use ID 2 from demo_patients.txt as default test
    test_id = sys.argv[1] if len(sys.argv) > 1 else "2"
    print(f"Testing with patient ID: {test_id}")
    context = fetch_patient_context(test_id)
    print(json.dumps(context, indent=2))
