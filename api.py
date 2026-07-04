import uuid, threading, time, traceback, sys
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict
from agent.orchestrator import Orchestrator

app = FastAPI(title="Beast Coder Agent")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# In-memory job store (reset on restart, but that's fine for our use case)
jobs: Dict[str, dict] = {}
job_lock = threading.Lock()

class TaskRequest(BaseModel):
    prompt: str = ""
    task: Optional[str] = None
    deep: bool = False

class CodeGenRequest(BaseModel):
    prompt: str = ""
    specification: Optional[str] = None
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
    return {"status": "healthy"}

# Background worker that actually calls Mistral and stores result
def run_job(job_id: str, task_type: str, *args):
    try:
        orch = Orchestrator()
        if task_type == "execute":
            prompt = args[0]
            deep = args[1] if len(args) > 1 else False
            result = orch.plan_and_execute_deep(prompt) if deep else orch.plan_and_execute(prompt)
        elif task_type == "generate_code":
            prompt, ctx = args[0], args[1] if len(args) > 1 else ""
            result = orch.generate_code(prompt, ctx)
        elif task_type == "self_improve":
            orig, prev = args[0], args[1]
            result = orch.self_improve(orig, prev)
        else:
            result = "Unknown task"
        with job_lock:
            jobs[job_id] = {"status": "done", "result": result}
    except Exception as e:
        with job_lock:
            jobs[job_id] = {"status": "error", "detail": str(e)}

def start_job(task_type: str, *args) -> str:
    job_id = str(uuid.uuid4())
    with job_lock:
        jobs[job_id] = {"status": "pending"}
    thread = threading.Thread(target=run_job, args=(job_id, task_type, *args), daemon=True)
    thread.start()
    return job_id

@app.post("/execute")
async def execute_task(req: TaskRequest):
    prompt = req.prompt or req.task or ""
    if not prompt:
        raise HTTPException(422, "Need prompt")
    job_id = start_job("execute", prompt, req.deep)
    return {"status": "accepted", "job_id": job_id}

@app.post("/generate-code")
async def generate_code(req: CodeGenRequest):
    prompt = req.prompt or req.specification or ""
    if not prompt:
        raise HTTPException(422, "Need prompt")
    job_id = start_job("generate_code", prompt, req.context)
    return {"status": "accepted", "job_id": job_id}

@app.post("/self-improve")
async def self_improve(req: SelfImproveRequest):
    job_id = start_job("self_improve", req.original_task, req.previous_response)
    return {"status": "accepted", "job_id": job_id}

@app.get("/status/{job_id}")
async def job_status(job_id: str):
    with job_lock:
        job = jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return job

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
