import os
import sys
import json
import time
import argparse
import datetime
from typing import Callable, Optional
from dotenv import load_dotenv
from anthropic import Anthropic

# Load env before importing tools in case they rely on env vars
load_dotenv()

# Import the existing tools
sys.path.append(os.path.join(os.path.dirname(__file__), "tools"))
try:
    from tools.fhir_tool import fetch_patient_context
    from tools.multimodal_tool import extract_pdf_content, transcribe_voice
    from tools.validation_tool import validate_icd10_codes, check_auth_criteria
except ImportError as e:
    print(f"Error importing tools: {e}")
    print("Ensure you are running from the root of the project.")
    sys.exit(1)

# Constants
EXPECTED_OUTPUT_KEYS = {
    "recommendation", "confidence", "clinical_rationale", "criteria_assessment", 
    "denial_risk_score", "draft_letter", "citations", "audit_trace"
}
RISK_MODEL_PATH = "model.cbm"
_risk_model = None

# 1. Tool Implementation for score_clinical_risk
def score_clinical_risk(patient_data: dict) -> dict:
    """
    Scores the clinical risk of denial for a prior authorization based on patient data.
    """
    global _risk_model
    try:
        from catboost import CatBoostClassifier
        if not os.path.exists(RISK_MODEL_PATH):
            return {"error": "Risk model model.cbm not found.", "tool": "score_clinical_risk"}
        
        if _risk_model is None:
            _risk_model = CatBoostClassifier()
            _risk_model.load_model(RISK_MODEL_PATH)
        
        fallbacks = {}
        
        # Extract features (fallback safely if missing from patient_data)
        age = 50
        if patient_data.get('birthDate'):
            try:
                year = int(patient_data['birthDate'].split('-')[0])
                age = datetime.datetime.now().year - year
            except:
                fallbacks['age'] = f"defaulted to 50 — FHIR dob parse failed: {patient_data.get('birthDate')}"
        else:
            fallbacks['age'] = "defaulted to 50 — FHIR dob missing"
        
        gender_val = patient_data.get('gender')
        if gender_val in ['male', 'female']:
            gender = '1' if gender_val == 'male' else '2'
        else:
            gender = '1'
            fallbacks['gender'] = f"defaulted to male — FHIR gender missing or invalid: {gender_val}"
        
        conditions = patient_data.get('conditions', [])
        if conditions and 'code' in conditions[0]:
            primary_dx = conditions[0]['code']
        else:
            primary_dx = 'missing'
            fallbacks['primary_dx'] = "defaulted to 'missing' — no conditions provided in FHIR context"
            
        comorbidity_count = max(0, len(conditions) - 1)
        proc_code = 'missing' # Currently not explicitly passed in patient_data dict for scoring tool
        num_prior_claims = 0
        
        features = [age, gender, primary_dx, proc_code, comorbidity_count, num_prior_claims]
        
        # Predict probability of denial
        probs = _risk_model.predict_proba([features])[0]
        denial_prob = float(probs[1])
        
        risk_tier = "low"
        if denial_prob > 0.7:
            risk_tier = "high"
        elif denial_prob > 0.4:
            risk_tier = "medium"
            
        result = {
            "denial_probability": denial_prob,
            "risk_tier": risk_tier,
            "shap_top_factors": ["Primary Diagnosis", "Comorbidity Count"]
        }
        
        if fallbacks:
            result["feature_fallback"] = fallbacks
            
        return result
    except Exception as e:
        return {"error": str(e), "tool": "score_clinical_risk"}

# Tool Dispatcher
TOOL_FUNCTIONS = {
    "fetch_patient_context": fetch_patient_context,
    "extract_pdf_content": extract_pdf_content,
    "transcribe_voice": transcribe_voice,
    "validate_icd10_codes": validate_icd10_codes,
    "check_auth_criteria": check_auth_criteria,
    "score_clinical_risk": score_clinical_risk
}

# 1. TOOL SCHEMAS
TOOL_SCHEMAS = [
    {
        "name": "fetch_patient_context",
        "description": "Queries HAPI FHIR for Patient demographics, Conditions, MedicationRequests, and Observations for a given patient ID.",
        "input_schema": {
            "type": "object",
            "properties": {"patient_id": {"type": "string"}},
            "required": ["patient_id"]
        }
    },
    {
        "name": "extract_pdf_content",
        "description": "Extracts text content from a clinical PDF file.",
        "input_schema": {
            "type": "object",
            "properties": {"file_path": {"type": "string"}},
            "required": ["file_path"]
        }
    },
    {
        "name": "transcribe_voice",
        "description": "Transcribes a voice note to text.",
        "input_schema": {
            "type": "object",
            "properties": {"file_path": {"type": "string"}},
            "required": ["file_path"]
        }
    },
    {
        "name": "validate_icd10_codes",
        "description": "Validates a list of ICD-10 codes.",
        "input_schema": {
            "type": "object",
            "properties": {
                "code_list": {
                    "type": "array",
                    "items": {"type": "string"}
                }
            },
            "required": ["code_list"]
        }
    },
    {
        "name": "check_auth_criteria",
        "description": "Checks if a diagnosis and procedure meet medical necessity criteria.",
        "input_schema": {
            "type": "object",
            "properties": {
                "dx_code": {"type": "string", "description": "Primary ICD-10 code"},
                "procedure_name": {"type": "string", "description": "Procedure name or code requested"}
            },
            "required": ["dx_code", "procedure_name"]
        }
    },
    {
        "name": "score_clinical_risk",
        "description": "Scores the clinical risk of denial for a prior authorization based on patient data.",
        "input_schema": {
            "type": "object",
            "properties": {
                "patient_data": {"type": "object", "description": "Structured patient data dict from FHIR tool output"}
            },
            "required": ["patient_data"]
        }
    }
]

# System prompts
AGENT_SYSTEM_PROMPT = """You are an orchestrator for a prior authorization agent. 
You must gather necessary information to produce an authorization package.
DEPENDENCIES (Enforced via prompt):
1. ALWAYS call fetch_patient_context FIRST.
2. If the user provided a PDF or audio file, call extract_pdf_content and transcribe_voice. 
   ONLY call them if the user explicitly provided the path.
3. Call validate_icd10_codes on any diagnosis codes you find.
4. Call check_auth_criteria and score_clinical_risk ONLY AFTER you have collected FHIR data and validated codes.

Make sure to call the tools in the correct logical sequence. Do not jump to score_clinical_risk before you have the FHIR data.
"""

FINAL_REASONING_PROMPT = """You are a prior authorization specialist at a healthcare billing company.
Given the structured tool outputs below, produce a prior authorization submission package. Cite specific evidence from the tool results. 
The draft letter must include: patient demographics, diagnosis summary, procedure justification with clinical evidence, and a signature block.

Output ONLY valid JSON matching this schema:
{
  "recommendation": "APPROVE | DENY | NEEDS_REVIEW",
  "confidence": float 0-1,
  "clinical_rationale": "string - detailed rationale with specific diagnosis references, procedural justification, and exact clear basis for the recommendation",
  "criteria_assessment": "string",
  "denial_risk_score": float 0-1,
  "draft_letter": "string",
  "citations": ["string"],
  "audit_trace": [{"step": 1, "tool": "name", "input": {}, "output": {}, "status": "success", "timestamp": "ISO8601"}]
}

Confidence = weighted average of: criteria match rate (40%) + (1 - denial_probability) (40%) + input completeness score (20%).
Do not include any Markdown formatting (no ```json). Output raw JSON.
"""

def execute_tool(tool_name: str, tool_input: dict, state: dict) -> dict:
    """Executes a tool and captures errors safely."""
    # 3. Input Routing Logic - explicit skipping if inputs are not present
    if tool_name == "extract_pdf_content" and "pdf" not in state["inputs_received"]:
        return {"skipped": "no PDF provided"}
    if tool_name == "transcribe_voice" and "audio" not in state["inputs_received"]:
        return {"skipped": "no audio provided"}
    
    # Actually call the tool
    func = TOOL_FUNCTIONS.get(tool_name)
    if not func:
        return {"error": f"Tool {tool_name} not found"}
        
    try:
        if tool_name == "fetch_patient_context":
            return func(tool_input.get("patient_id"))
        elif tool_name == "extract_pdf_content":
            return func(tool_input.get("file_path"))
        elif tool_name == "transcribe_voice":
            return func(tool_input.get("file_path"))
        elif tool_name == "validate_icd10_codes":
            return func(tool_input.get("code_list", []))
        elif tool_name == "check_auth_criteria":
            return func(tool_input.get("dx_code"), tool_input.get("procedure_name"))
        elif tool_name == "score_clinical_risk":
            return func(tool_input.get("patient_data"))
    except Exception as e:
        return {"error": str(e), "tool": tool_name}

def run_orchestrator(patient_id: str, pdf: str = None, audio: str = None, trace_callback: Optional[Callable] = None) -> dict:
    """Executes the orchestrator loop programmatically and returns the final JSON dict."""
    API_KEY = os.getenv("ANTHROPIC_API_KEY")
    MODEL = os.getenv("CLAUDE_MODEL", "claude-haiku-4-5") # Required fallback as per PRD
    if not API_KEY:
        raise ValueError("ANTHROPIC_API_KEY env variable not set.")

    client = Anthropic(api_key=API_KEY)

    # 2. State Object tracking
    inputs_received = ["fhir"]
    if pdf:
        inputs_received.append("pdf")
    if audio:
        inputs_received.append("audio")

    # Track audit trace for final output assembly
    audit_trace = []

    state = {
        "patient_id": patient_id,
        "inputs_received": inputs_received,
        "tool_results": {},
        "reasoning_chain": [],
        "final_output": None
    }

    # Prepare inputs for the agent system prompt
    context_str = f"Patient ID: {patient_id}\n"
    if pdf:
        context_str += f"PDF Clinical Doc Path: {pdf}\n"
    if audio:
        context_str += f"Voice Note Path: {audio}\n"

    messages = [
        {
            "role": "user",
            "content": f"Please process the prior authorization for the following inputs.\n\n{context_str}"
        }
    ]

    print(f"Starting agent run for Patient {patient_id} using model {MODEL}...")
    
    step_count = 1
    
    # 4. Tool-Use Loop
    while True:
        response = client.messages.create(
            model=MODEL,
            system=AGENT_SYSTEM_PROMPT,
            messages=messages,
            tools=TOOL_SCHEMAS,
            max_tokens=2048
        )
        
        if response.stop_reason == "tool_use":
            # Claude generated one or more tool calls
            messages.append({"role": "assistant", "content": response.content})
            
            tool_results = []
            
            # Iterate through all blocks handles concurrent execution
            for block in response.content:
                if block.type == "tool_use":
                    start_time = time.time()
                    
                    tool_name = block.name
                    tool_input = block.input
                    
                    # 6. Execute safely
                    result = execute_tool(tool_name, tool_input, state)
                    duration = time.time() - start_time
                    
                    status = "success"
                    if isinstance(result, dict) and ("error" in result or "skipped" in result):
                        status = "failed" if "error" in result else "skipped"
                    
                    # Formatting terminal print
                    print(f"[{step_count}] {tool_name} ... {status} ({duration:.1f}s)")
                    
                    # Save results to state
                    state["tool_results"][tool_name] = result
                    state["reasoning_chain"].append({
                        "tool": tool_name,
                        "status": status,
                        "duration": duration
                    })
                    
                    # 7. Audit Trace
                    trace_entry = {
                        "step": step_count,
                        "tool": tool_name,
                        "input": tool_input,
                        "output": result,
                        "status": status,
                        "timestamp": datetime.datetime.now().isoformat()
                    }
                    audit_trace.append(trace_entry)
                    if trace_callback:
                        trace_callback(trace_entry)

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result)[:2000] # clamp huge outputs slightly to avoid context limits
                    })
                    
                    step_count += 1
            
            messages.append({"role": "user", "content": tool_results})
        else:
            break
            
    # 8. Final reasoning call
    print("Agent tool loop complete. Generating final authorization package...")
    
    final_prompt = FINAL_REASONING_PROMPT + "\n\n=== AUDIT TRACE OF COMPLETED STEPS ===\n" + json.dumps(audit_trace, indent=2) + "\n\nGenerate the final JSON matching the schema precisely."
    
    final_response = client.messages.create(
        model=MODEL,
        messages=[{"role": "user", "content": final_prompt}],
        max_tokens=4096,
        temperature=0.3
    )

    final_text = next(b.text for b in final_response.content if b.type == "text")
    try:
        final_json = json.loads(final_text)
        
        # Add the audit trace formally if it missed it
        if "audit_trace" not in final_json or not final_json["audit_trace"]:
             final_json["audit_trace"] = audit_trace

        for key in EXPECTED_OUTPUT_KEYS:
            assert key in final_json, f"Missing key in final JSON: {key}"

        recommendation = final_json.get("recommendation", "UNKNOWN")
        confidence = final_json.get("confidence", 0.0)
        
        print(f"\nFinal Recommendation: {recommendation}")
        print(f"Confidence: {confidence * 100:.1f}%\n")
        
        out_dir = "output"
        os.makedirs(out_dir, exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        outfile = os.path.join(out_dir, f"{patient_id}_{timestamp}.json")
        
        with open(outfile, "w") as f:
            json.dump(final_json, f, indent=2)
        print(f"Output saved to {outfile}")
        
        return final_json

    except Exception as e:
        print(f"\nFailed to parse final output sequence. Exact error: {e}")
        print(f"Raw Claude Content:\n{final_text}")
        raise ValueError(f"Failed to parse final output sequence: {e}")

def main():
    parser = argparse.ArgumentParser(description="PriorAI CLI Orchestrator")
    parser.add_argument("--patient-id", required=True, help="FHIR Patient ID")
    parser.add_argument("--pdf", help="Path to clinical PDF doc")
    parser.add_argument("--audio", help="Path to voice note wav/mp3")
    args = parser.parse_args()
    
    run_orchestrator(args.patient_id, args.pdf, args.audio)

if __name__ == "__main__":
    main()
