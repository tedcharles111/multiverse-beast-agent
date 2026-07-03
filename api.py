import traceback, sys, os, time, threading, requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

# Attempt to import Orchestrator safely
Orchestrator = None
import_error = None
try:
    from agent.orchestrator import Orchestrator as _Orch
    Orchestrator = _Orch
except Exception as e:
    import_error = traceback.format_exc()
    print("CRITICAL: Orchestrator import failed", file=sys.stderr)
    print(import_error, file=sys.stderr)

app = FastAPI(title="Beast Coder Agent")

# CORS middleware (always active, even if orchestrator is dead)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

class TaskRequest(BaseModel):
    task: Optional[str] = None
    prompt: Optional[str] = None
    deep: bool = False

class CodeGenRequest(BaseModel):
    specification: Optional[str] = None
    prompt: Optional[str] = None
    context: str = ""

class SelfImproveRequest(BaseModel):
    original_task: str
    previous_response: str

@app.options("/health")
@app.options("/execute")
@app.options("/generate-code")
@app.options("/self-improve")
async def options_all():
    return {}

@app.get("/health")
async def health():
    if Orchestrator is None:
        return {"status": "degraded", "error": "Orchestrator not loaded"}
    return {"status": "healthy"}

def get_orchestrator():
    if Orchestrator is None:
        raise HTTPException(503, f"Agent not available: {import_error[:200] if import_error else 'Unknown error'}")
    return Orchestrator()

@app.post("/execute")
async def execute_task(request: TaskRequest):
    task = request.prompt or request.task or ""
    if not task:
        raise HTTPException(422, "Need prompt")
    try:
        orch = get_orchestrator()
        result = orch.plan_and_execute(task) if not request.deep else orch.plan_and_execute_deep(task)
        return {"status": "success", "result": result}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))

@app.post("/generate-code")
async def generate_code(request: CodeGenRequest):
    prompt = request.prompt or request.specification or ""
    if not prompt:
        raise HTTPException(422, "Need prompt")
    try:
        orch = get_orchestrator()
        code = orch.generate_code(prompt, request.context)
        return {"status": "success", "code": code}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))

@app.post("/self-improve")
async def self_improve(request: SelfImproveRequest):
    try:
        orch = get_orchestrator()
        improved = orch.self_improve(request.original_task, request.previous_response)
        return {"status": "success", "improved_result": improved}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))

# Background keep‑alive to prevent cold starts
def keep_alive():
    time.sleep(30)
    while True:
        try:
            requests.get("http://localhost:8000/health", timeout=5)
        except Exception:
            pass
        time.sleep(300)  # every 5 minutes

@app.on_event("startup")
async def startup_event():
    threading.Thread(target=keep_alive, daemon=True).start()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
