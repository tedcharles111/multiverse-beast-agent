from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
from agent.orchestrator import Orchestrator
import uvicorn

app = FastAPI(title="AI Coding Agent API")

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
    original_task: Optional[str] = None
    prompt: Optional[str] = Field(None, alias="original_task_alias")  # Not used, just for compatibility
    previous_response: str

    def get_original_task(self) -> str:
        return self.original_task or ""

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
        raise HTTPException(status_code=500, detail=str(e))

@app.options("/generate-code")
async def options_generate():
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
        raise HTTPException(status_code=500, detail=str(e))

@app.options("/self-improve")
async def options_self_improve():
    return {}

@app.post("/self-improve")
async def self_improve(request: SelfImproveRequest):
    if not request.original_task and not request.previous_response:
        raise HTTPException(status_code=422, detail="'original_task' and 'previous_response' are required")
    try:
        improved = orchestrator.self_improve(request.original_task, request.previous_response)
        return {"status": "success", "improved_result": improved}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
