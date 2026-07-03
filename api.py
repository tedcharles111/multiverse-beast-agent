from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from agent.orchestrator import Orchestrator
import uvicorn

app = FastAPI(title="Beast Coder Agent")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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

@app.options("/execute")
async def options_exec(): return {}
@app.post("/execute")
async def execute_task(request: TaskRequest):
    task = request.get_task()
    if not task:
        raise HTTPException(422, "Need task or prompt")
    try:
        result = orchestrator.plan_and_execute(task) if not request.deep else orchestrator.plan_and_execute_deep(task)
        return {"status": "success", "result": result}
    except Exception as e:
        raise HTTPException(500, str(e))

@app.options("/generate-code")
async def options_gen(): return {}
@app.post("/generate-code")
async def generate_code(request: CodeGenRequest):
    spec = request.get_specification()
    if not spec:
        raise HTTPException(422, "Need specification or prompt")
    try:
        return {"status": "success", "code": orchestrator.generate_code(spec, request.context)}
    except Exception as e:
        raise HTTPException(500, str(e))

@app.options("/self-improve")
async def options_improve(): return {}
@app.post("/self-improve")
async def self_improve(request: SelfImproveRequest):
    try:
        improved = orchestrator.self_improve(request.original_task, request.previous_response)
        return {"status": "success", "improved_result": improved}
    except Exception as e:
        raise HTTPException(500, str(e))

@app.get("/health")
async def health(): return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
