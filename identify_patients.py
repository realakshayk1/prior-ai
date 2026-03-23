import requests

FHIR_BASE = "http://localhost:8080/fhir/"

def get_patients():
    r = requests.get(f"{FHIR_BASE}Patient?_count=100")
    return r.json().get("entry", [])

def check_patient(p_id):
    # Check conditions
    r_cond = requests.get(f"{FHIR_BASE}Condition?patient={p_id}&_count=20")
    cond_count = len(r_cond.json().get("entry", []))
    
    # Check medications
    r_med = requests.get(f"{FHIR_BASE}MedicationRequest?patient={p_id}&_count=20")
    med_count = len(r_med.json().get("entry", []))
    
    return cond_count, med_count

if __name__ == "__main__":
    print("Fetching patients...")
    entries = get_patients()
    demo_ids = []
    
    for entry in entries:
        p_id = entry["resource"]["id"]
        cond, med = check_patient(p_id)
        print(f"Patient {p_id}: {cond} conditions, {med} medications")
        
        if cond >= 5 and med >= 3:
            demo_ids.append(p_id)
            print(f"  FOUND GOOD DEMO PATIENT: {p_id}")
            if len(demo_ids) >= 5:
                break
                
    with open("demo_patients.txt", "w") as f:
        f.write("\n".join(demo_ids))
    print(f"\nSaved {len(demo_ids)} IDs to demo_patients.txt")
