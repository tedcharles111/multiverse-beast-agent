import traceback, sys, time, threading, requests
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
from agent.orchestrator import Orchestrator

app = FastAPI(title="Beast Coder Agent")

# Global CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Global exception handler to force CORS on errors
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)},
        headers={"Access-Control-Allow-Origin": "*"}
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
    return {"status": "healthy"}

def get_orch():
    return Orchestrator()

@app.post("/execute")
async def execute_task(req: TaskRequest):
    prompt = req.prompt or req.task or ""
    if not prompt:
        raise HTTPException(422, "Need prompt")
    try:
        orch = get_orch()
        result = orch.plan_and_execute(prompt) if not req.deep else orch.plan_and_execute_deep(prompt)
        return JSONResponse(content={"status": "success", "result": result})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))

@app.post("/generate-code")
async def generate_code(req: CodeGenRequest):
    prompt = req.prompt or req.specification or ""
    if not prompt:
        raise HTTPException(422, "Need prompt")
    try:
        orch = get_orch()
        code = orch.generate_code(prompt, req.context)
        return JSONResponse(content={"status": "success", "code": code})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))

@app.post("/self-improve")
async def self_improve(req: SelfImproveRequest):
    try:
        orch = get_orch()
        improved = orch.self_improve(req.original_task, req.previous_response)
        return JSONResponse(content={"status": "success", "improved_result": improved})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))

# Keep‑alive thread
def keep_alive():
    time.sleep(30)
    while True:
        try:
            requests.get("http://localhost:8000/health", timeout=5)
        except:
            pass
        time.sleep(300)

@app.on_event("startup")
async def startup():
    threading.Thread(target=keep_alive, daemon=True).start()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
