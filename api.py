from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from agent.orchestrator import Orchestrator
import uvicorn
import requests
import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Beast Coder Agent")

# --- CORS: allow all origins ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

orchestrator = Orchestrator()

class TaskRequest(BaseModel):
    task: Optional[str] = None
    prompt: Optional[str] = None
    deep: bool = False

    def get_task(self) -> str:
        return self.task or self.prompt or ""

class CodeGenRequest(BaseModel):
    specification: Optional[str] = None
    prompt: Optional[str] = None
    context: str = ""

    def get_specification(self) -> str:
        return self.specification or self.prompt or ""

class SelfImproveRequest(BaseModel):
    original_task: str
    previous_response: str

@app.on_event("startup")
async def startup_event():
    """Start background keep-alive task."""
    asyncio.create_task(keep_alive_ping())

async def keep_alive_ping():
    """Ping /health every 10 minutes to prevent Render idle shutdown."""
    await asyncio.sleep(60)  # wait a minute after startup
    while True:
        try:
            requests.get("https://multiverse-beast-agent.onrender.com/health", timeout=10)
            logger.info("Keep-alive ping sent")
        except Exception as e:
            logger.error(f"Keep-alive ping failed: {e}")
        await asyncio.sleep(600)  # 10 minutes

@app.get("/health")
async def health():
    return {"status": "healthy"}

# Explicit OPTIONS handlers for CORS preflight
@app.options("/execute")
async def options_execute():
    return {}

@app.post("/execute")
async def execute_task(request: TaskRequest):
    task_text = request.get_task()
    if not task_text:
        raise HTTPException(status_code=422, detail="Either 'task' or 'prompt' field is required")
    try:
        if request.deep:
            result = orchestrator.plan_and_execute_deep(task_text)
        else:
            result = orchestrator.plan_and_execute(task_text)
        return {"status": "success", "result": result}
    except Exception as e:
        logger.exception("Execute failed")
        raise HTTPException(status_code=500, detail=str(e))

@app.options("/generate-code")
async def options_generate_code():
    return {}

@app.post("/generate-code")
async def generate_code(request: CodeGenRequest):
    spec = request.get_specification()
    if not spec:
        raise HTTPException(status_code=422, detail="Either 'specification' or 'prompt' field is required")
    try:
        code = orchestrator.generate_code(spec, request.context)
        return {"status": "success", "code": code}
    except Exception as e:
        logger.exception("Generate code failed")
        raise HTTPException(status_code=500, detail=str(e))

@app.options("/self-improve")
async def options_self_improve():
    return {}

@app.post("/self-improve")
async def self_improve(request: SelfImproveRequest):
    if not request.original_task or not request.previous_response:
        raise HTTPException(status_code=422, detail="Both 'original_task' and 'previous_response' are required")
    try:
        improved = orchestrator.self_improve(request.original_task, request.previous_response)
        return {"status": "success", "improved_result": improved}
    except Exception as e:
        logger.exception("Self-improve failed")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
