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

@app.get("/health")
async def health(): return {"status": "healthy"}

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

@app.post("/generate-code")
async def generate_code(request: CodeGenRequest):
    spec = request.get_specification()
    if not spec:
        raise HTTPException(422, "Need specification or prompt")
    try:
        return {"status": "success", "code": orchestrator.generate_code(spec, request.context)}
    except Exception as e:
        raise HTTPException(500, str(e))

@app.post("/self-improve")
async def self_improve(request: SelfImproveRequest):
    try:
        improved = orchestrator.self_improve(request.original_task, request.previous_response)
        return {"status": "success", "improved_result": improved}
    except Exception as e:
        raise HTTPException(500, str(e))

# --- NEW: isolated deployment test endpoint (cannot crash main agent) ---
@app.post("/deploy-netlify")
async def deploy_netlify_test():
    """Calls the Netlify REST API directly to deploy a tiny HTML file."""
    import os, io, zipfile, requests
    token = os.getenv('NETLIFY_AUTH_TOKEN')
    if not token:
        return {"status": "error", "detail": "NETLIFY_AUTH_TOKEN not set"}
    # Create a minimal zip with index.html
    html = b"<html><body><h1>Beast is live on Netlify!</h1></body></html>"
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('index.html', html)
    zip_buf.seek(0)
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/zip'}
    # Create a new site
    site_resp = requests.post('https://api.netlify.com/api/v1/sites', headers={'Authorization': f'Bearer {token}'}, json={})
    if site_resp.status_code != 201:
        return {"status": "error", "detail": f"Site creation failed: {site_resp.text}"}
    site_id = site_resp.json()['id']
    # Deploy the zip
    deploy_resp = requests.post(f'https://api.netlify.com/api/v1/sites/{site_id}/deploys', headers=headers, data=zip_buf)
    if deploy_resp.status_code == 200:
        url = deploy_resp.json().get('deploy_ssl_url') or deploy_resp.json().get('url')
        return {"status": "success", "url": url}
    else:
        return {"status": "error", "detail": deploy_resp.text}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
