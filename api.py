import traceback, sys, time, threading, concurrent.futures
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
from agent.orchestrator import Orchestrator

app = FastAPI(title="Beast Coder Agent")

# --- CORS: applied to every single response, no exceptions ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# --- Global exception handler (forces CORS even on 500/503) ---
@app.exception_handler(Exception)
async def universal_handler(request: Request, exc: Exception):
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

# Helper: run a function with a timeout (in seconds)
def run_with_timeout(func, timeout_sec, *args, **kwargs):
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(func, *args, **kwargs)
        try:
            return future.result(timeout=timeout_sec)
        except concurrent.futures.TimeoutError:
            raise TimeoutError(f"Operation timed out after {timeout_sec}s")

@app.post("/execute")
async def execute_task(req: TaskRequest):
    prompt = req.prompt or req.task or ""
    if not prompt:
        raise HTTPException(422, "Need prompt")
    try:
        orch = Orchestrator()
        # 90-second hard timeout for the whole Mistral call
        result = run_with_timeout(
            orch.plan_and_execute_deep if req.deep else orch.plan_and_execute,
            90, prompt
        )
        return JSONResponse(content={"status": "success", "result": result})
    except TimeoutError:
        return JSONResponse(
            status_code=503,
            content={"status": "error", "detail": "Agent took too long – please retry"},
            headers={"Access-Control-Allow-Origin": "*"}
        )
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"detail": str(e)},
            headers={"Access-Control-Allow-Origin": "*"}
        )

@app.post("/generate-code")
async def generate_code(req: CodeGenRequest):
    prompt = req.prompt or req.specification or ""
    if not prompt:
        raise HTTPException(422, "Need prompt")
    try:
        orch = Orchestrator()
        code = run_with_timeout(orch.generate_code, 90, prompt, req.context)
        return JSONResponse(content={"status": "success", "code": code})
    except TimeoutError:
        return JSONResponse(
            status_code=503,
            content={"status": "error", "detail": "Agent took too long – please retry"},
            headers={"Access-Control-Allow-Origin": "*"}
        )
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"detail": str(e)},
            headers={"Access-Control-Allow-Origin": "*"}
        )

@app.post("/self-improve")
async def self_improve(req: SelfImproveRequest):
    try:
        orch = Orchestrator()
        improved = run_with_timeout(orch.self_improve, 90, req.original_task, req.previous_response)
        return JSONResponse(content={"status": "success", "improved_result": improved})
    except TimeoutError:
        return JSONResponse(
            status_code=503,
            content={"status": "error", "detail": "Agent took too long – please retry"},
            headers={"Access-Control-Allow-Origin": "*"}
        )
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"detail": str(e)},
            headers={"Access-Control-Allow-Origin": "*"}
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
