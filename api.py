from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import uvicorn, traceback, sys

# Log any import errors
try:
    from agent.orchestrator import Orchestrator
except Exception as e:
    print("IMPORT FAILED", file=sys.stderr)
    traceback.print_exc()
    Orchestrator = None

app = FastAPI(title="Beast Coder Agent")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

class TaskRequest(BaseModel):
    prompt: str = ""
    task: Optional[str] = None
    deep: bool = False

class CodeGenRequest(BaseModel):
    prompt: str = ""
    specification: Optional[str] = None
    context: str = ""

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.post("/execute")
async def execute(req: TaskRequest):
    if not Orchestrator: raise HTTPException(500, "Agent not initialized")
    prompt = req.prompt or req.task or ""
    if not prompt: raise HTTPException(422, "Need prompt")
    try:
        orch = Orchestrator()
        res = orch.plan_and_execute(prompt) if not req.deep else orch.plan_and_execute_deep(prompt)
        return {"status": "success", "result": res}
    except Exception as e:
        raise HTTPException(500, str(e))

@app.post("/generate-code")
async def gen_code(req: CodeGenRequest):
    if not Orchestrator: raise HTTPException(500, "Agent not initialized")
    prompt = req.prompt or req.specification or ""
    if not prompt: raise HTTPException(422, "Need prompt")
    try:
        orch = Orchestrator()
        code = orch.generate_code(prompt, req.context)
        return {"status": "success", "code": code}
    except Exception as e:
        raise HTTPException(500, str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
