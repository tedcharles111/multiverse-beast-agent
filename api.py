from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from agent.orchestrator import Orchestrator
import uvicorn

app = FastAPI(title="AI Coding Agent API")
orchestrator = Orchestrator()

class TaskRequest(BaseModel):
    task: str
    deep: bool = False  # Set to True for deep thinking mode

class CodeGenRequest(BaseModel):
    specification: str
    context: str = ""

class SelfImproveRequest(BaseModel):
    original_task: str
    previous_response: str

@app.post("/execute")
async def execute_task(request: TaskRequest):
    try:
        if request.deep:
            result = orchestrator.plan_and_execute_deep(request.task)
        else:
            result = orchestrator.plan_and_execute(request.task)
        return {"status": "success", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate-code")
async def generate_code(request: CodeGenRequest):
    try:
        code = orchestrator.generate_code(request.specification, request.context)
        return {"status": "success", "code": code}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/self-improve")
async def self_improve(request: SelfImproveRequest):
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
