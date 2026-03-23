import os
import sys
import uuid
import json
import asyncio
import httpx
import datetime
from typing import Optional, Dict

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

# Add parent directory to path to import run_agent
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from run_agent import run_orchestrator
except ImportError as e:
    print(f"Error importing run_orchestrator: {e}")
    sys.exit(1)

app = FastAPI(title="PriorAI Backend")

# Enable CORS for React dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class RunState:
    def __init__(self):
        self.status = "running"
        self.audit_trace = []
        self.final_output = None
        self.error = None

runs: Dict[str, RunState] = {}

def bg_run_agent(run_id: str, patient_id: str, pdf_path: Optional[str], audio_path: Optional[str]):
    """Background task to run the agent."""
    state = runs[run_id]
    
    def trace_callback(trace_entry: dict):
        state.audit_trace.append(trace_entry)
        
    try:
        final_output = run_orchestrator(
            patient_id=patient_id, 
            pdf=pdf_path, 
            audio=audio_path, 
            trace_callback=trace_callback
        )
        state.final_output = final_output
        state.status = "complete"
    except Exception as e:
        state.status = "error"
        state.error = str(e)
        state.audit_trace.append({
            "step": "error",
            "tool": "orchestrator",
            "input": {},
            "output": {"error": str(e)},
            "status": "failed",
            "timestamp": datetime.datetime.now().isoformat()
        })

@app.post("/run")
async def start_run(
    background_tasks: BackgroundTasks,
    patient_id: str = Form(...),
    pdf: Optional[UploadFile] = File(None),
    audio: Optional[UploadFile] = File(None)
):
    """Starts a new agent run."""
    run_id = str(uuid.uuid4())
    runs[run_id] = RunState()
    
    # Save files to tmp/<run_id>/ if provided
    tmp_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tmp", run_id)
    os.makedirs(tmp_dir, exist_ok=True)
    
    pdf_path = None
    if pdf:
        pdf_path = os.path.join(tmp_dir, pdf.filename)
        with open(pdf_path, "wb") as f:
            f.write(await pdf.read())
            
    audio_path = None
    if audio:
        audio_path = os.path.join(tmp_dir, audio.filename)
        with open(audio_path, "wb") as f:
            f.write(await audio.read())
            
    # Spawn background task
    background_tasks.add_task(bg_run_agent, run_id, patient_id, pdf_path, audio_path)
    
    return {"run_id": run_id}

@app.get("/stream/{run_id}")
async def stream_run(run_id: str):
    """Streams the audit trace of the agent run via Server-Sent Events."""
    if run_id not in runs:
        raise HTTPException(status_code=404, detail="Run ID not found")
        
    async def event_generator():
        state = runs[run_id]
        last_yielded_index = 0
        
        while True:
            # Yield any new events
            while last_yielded_index < len(state.audit_trace):
                event = state.audit_trace[last_yielded_index]
                last_yielded_index += 1
                yield {"data": json.dumps(event)}
                
            if state.status in ("complete", "error"):
                # Yield any remaining events
                while last_yielded_index < len(state.audit_trace):
                    event = state.audit_trace[last_yielded_index]
                    last_yielded_index += 1
                    yield {"data": json.dumps(event)}
                    
                # Send the final complete event
                yield {"data": "complete"}
                break
                
            await asyncio.sleep(0.5)

    return EventSourceResponse(event_generator())

@app.get("/result/{run_id}")
async def get_result(run_id: str):
    """Returns the final JSON package from the run state."""
    if run_id not in runs:
        raise HTTPException(status_code=404, detail="Run ID not found")
        
    state = runs[run_id]
    if state.status == "running":
        return {"status": "pending"}
    elif state.status == "error":
        return {"status": "error", "error": state.error}
    else:
        return state.final_output

@app.get("/patients")
async def get_patients():
    """Calls FHIR Patient?_count=20 and returns a summary list."""
    fhir_base_url = os.getenv("FHIR_BASE_URL", "http://localhost:8080/fhir")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{fhir_base_url}/Patient?_count=20", timeout=10.0)
            response.raise_for_status()
            data = response.json()
            
            patients = []
            for entry in data.get("entry", []):
                resource = entry.get("resource", {})
                pid = resource.get("id", "Unknown")
                
                # Use family + first given if present, fallback to "Unknown"
                name_list = resource.get("name", [])
                name_str = "Unknown"
                if name_list:
                    name_obj = name_list[0]
                    family = name_obj.get("family", "")
                    given = name_obj.get("given", [])
                    given_str = given[0] if given else ""
                    
                    if family and given_str:
                        name_str = f"{family}, {given_str}"
                    elif family:
                        name_str = family
                    elif given_str:
                        name_str = given_str
                    elif name_obj.get("text"):
                        name_str = name_obj.get("text")

                # Parse birthDate and calculate age
                birth_date_str = resource.get("birthDate")
                age = None
                if birth_date_str:
                    try:
                        birth_date = datetime.date.fromisoformat(birth_date_str)
                        today = datetime.date.today()
                        age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
                    except ValueError:
                        pass # age remains None
                
                patients.append({"id": pid, "name": name_str, "age": age})
                
            return patients
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
