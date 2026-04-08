from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from agent.orchestrator import Orchestrator
import uvicorn

app = FastAPI(title="AI Coding Agent API")
orchestrator = Orchestrator()

class TaskRequest(BaseModel):
    task: str
    stream: bool = False

class CodeGenRequest(BaseModel):
    specification: str
    context: str = ""

@app.post("/execute")
async def execute_task(request: TaskRequest):
    try:
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

@app.get("/health")
async def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
