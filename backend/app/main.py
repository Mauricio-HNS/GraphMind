from pathlib import Path
from uuid import uuid4
import json
import shutil
from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data" / "jobs"
FRONTEND = ROOT / "frontend" / "index.html"
JOBS: dict[str, dict] = {}
API_KEYS: dict[str, str] = {}
SUPPORTED = {".png", ".jpg", ".jpeg", ".webp"}

app = FastAPI(title="GraphMind API", version="0.4.0", description="Turn visual data into AI-ready knowledge and deliver it through APIs, webhooks and exports.")

class JobResponse(BaseModel):
    job_id: str
    status: str
    files: int
    prompt: str

class ApiAccessResponse(BaseModel):
    job_id: str
    api_key: str
    base_url: str
    endpoints: dict[str, str]

class WebhookRequest(BaseModel):
    url: str


def require_key(job_id: str, authorization: str | None) -> None:
    key = API_KEYS.get(job_id)
    if not key:
        raise HTTPException(404, "Integration access has not been generated for this job")
    if authorization != f"Bearer {key}":
        raise HTTPException(401, "Invalid API key")


def get_job_or_404(job_id: str) -> dict:
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return job

@app.get("/", include_in_schema=False)
def frontend():
    return FileResponse(FRONTEND)

@app.get("/health")
def health():
    return {"status": "ok", "service": "graphmind", "version": "0.4.0"}

@app.post("/api/v1/jobs", response_model=JobResponse)
async def create_job(prompt: str = Form(...), files: list[UploadFile] = File(...)):
    job_id = str(uuid4())
    root = DATA_DIR / job_id
    root.mkdir(parents=True, exist_ok=True)
    accepted = []
    for file in files:
        name = Path(file.filename or "upload").name
        if Path(name).suffix.lower() not in SUPPORTED:
            continue
        target = root / name
        with target.open("wb") as out:
            shutil.copyfileobj(file.file, out)
        accepted.append(str(target))
    if not accepted:
        raise HTTPException(400, "No supported chart images uploaded")
    from app.services.processor import process_file
    results = [process_file(path, prompt) for path in accepted]
    JOBS[job_id] = {"status": "completed", "prompt": prompt, "charts": results, "webhook": None}
    return JobResponse(job_id=job_id, status="completed", files=len(accepted), prompt=prompt)

@app.get("/api/v1/jobs/{job_id}")
def get_job(job_id: str):
    job = get_job_or_404(job_id)
    return {"job_id": job_id, "status": job["status"], "charts": len(job["charts"])}

@app.get("/api/v1/jobs/{job_id}/results")
def get_results(job_id: str):
    job = get_job_or_404(job_id)
    return {"job_id": job_id, **job}

@app.post("/api/v1/integrations/{job_id}/access", response_model=ApiAccessResponse)
def create_integration_access(job_id: str):
    get_job_or_404(job_id)
    from app.services.delivery import DeliveryService
    key = DeliveryService.create_api_key()
    API_KEYS[job_id] = key
    return ApiAccessResponse(
        job_id=job_id,
        api_key=key,
        base_url="/api/v1/integrations/" + job_id,
        endpoints={
            "data": f"/api/v1/integrations/{job_id}/data",
            "status": f"/api/v1/jobs/{job_id}",
            "results": f"/api/v1/jobs/{job_id}/results",
            "manifest": f"/api/v1/integrations/{job_id}/manifest",
        },
    )

@app.get("/api/v1/integrations/{job_id}/data")
def integration_data(job_id: str, authorization: str | None = Header(default=None)):
    require_key(job_id, authorization)
    job = get_job_or_404(job_id)
    return JSONResponse({"job_id": job_id, "data": job["charts"]})

@app.get("/api/v1/integrations/{job_id}/manifest")
def integration_manifest(job_id: str, authorization: str | None = Header(default=None)):
    require_key(job_id, authorization)
    job = get_job_or_404(job_id)
    from app.services.delivery import DeliveryService
    return DeliveryService.manifest(job_id, job)

@app.get("/api/v1/integrations/{job_id}/json")
def integration_json(job_id: str, authorization: str | None = Header(default=None)):
    require_key(job_id, authorization)
    job = get_job_or_404(job_id)
    return JSONResponse(DeliveryService.public_payload(job_id, job))

@app.post("/api/v1/integrations/{job_id}/webhook")
def configure_webhook(job_id: str, request: WebhookRequest, authorization: str | None = Header(default=None)):
    require_key(job_id, authorization)
    get_job_or_404(job_id)["webhook"] = request.url
    return {"job_id": job_id, "webhook": request.url, "status": "configured"}

@app.get("/api/v1/integrations/{job_id}/openapi")
def integration_openapi(job_id: str, authorization: str | None = Header(default=None)):
    require_key(job_id, authorization)
    get_job_or_404(job_id)
    return {
        "name": "GraphMind Integration API",
        "version": "1.0",
        "authentication": "Bearer API key",
        "endpoints": {
            "GET /data": "Structured chart knowledge",
            "GET /json": "Complete JSON payload",
            "GET /manifest": "Delivery manifest and checksums",
            "POST /webhook": "Configure result webhook",
        },
    }

@app.get("/api/v1/integrations/{job_id}/download.json")
def download_json(job_id: str, authorization: str | None = Header(default=None)):
    require_key(job_id, authorization)
    job = get_job_or_404(job_id)
    payload = json.dumps({"job_id": job_id, **job}, ensure_ascii=False, indent=2)
    return JSONResponse(content={"filename": f"graphmind-{job_id}.json", "content": payload})
