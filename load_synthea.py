import json, requests
from pathlib import Path

import os
FHIR_BASE = os.environ.get("FHIR_BASE_URL", "http://localhost:8080/fhir/")
SYNTHEA_DIR = Path("./synthea_output/fhir")

def load_bundle(file_path):
    with open(file_path, encoding="utf-8") as f:
        bundle = json.load(f)
    # Load infrastructure first
    infra_files = [f for f in SYNTHEA_DIR.glob("*.json") 
                   if f.name.startswith(("hospital", "practitioner"))]
    print(f"Loading {len(infra_files)} infrastructure bundles...")
    for f in infra_files:
        status, name = load_bundle(f)
        print(f"  {name}: {status}")

    # Load patient bundles
    patient_files = [f for f in SYNTHEA_DIR.glob("*.json")
                     if not f.name.startswith(("hospital", "practitioner"))]
    print(f"Loading {len(patient_files)} patient bundles...")
    success, failed = 0, 0
    for i, f in enumerate(patient_files):
        status, name = load_bundle(f)
        if status in (200, 201):
            success += 1
        else:
            failed += 1
            print(f"  FAILED ({status}): {name}")
        if (i + 1) % 20 == 0:
            print(f"  {i+1}/{len(patient_files)} loaded...")
    print(f"\nDone. {success} succeeded, {failed} failed.")
    r = requests.get(f"{FHIR_BASE}/Patient?_count=1&_summary=count")
    print(f"HAPI now has {r.json().get('total', '?')} Patient resources.")
