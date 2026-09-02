from pathlib import Path
from uuid import uuid4
import json
import shutil
import threading
import urllib.request
import secrets
from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel
from app.services.chart_knowledge import CHART_KNOWLEDGE, SEMANTIC_TERMS
from app.services.delivery import DeliveryService
from app.services.chart_analysis import analyze_job

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data" / "jobs"
FRONTEND = ROOT / "frontend" / "app.html"
JOBS: dict[str, dict] = {}
API_KEYS: dict[str, str] = {}
SHARES: dict[str, str] = {}
SUPPORTED = {".png", ".jpg", ".jpeg", ".webp", ".pdf", ".csv", ".xlsx", ".xls", ".zip"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}

app = FastAPI(title="GraphMind API", version="0.7.0", description="Turn visual data into AI-ready knowledge and deliver it through APIs, webhooks and exports.")

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


def get_job_or_404(job_id: str) -> dict:
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return job


def require_key(job_id: str, authorization: str | None) -> None:
    key = API_KEYS.get(job_id)
    if not key:
        raise HTTPException(404, "Integration access has not been generated for this job")
    if authorization != f"Bearer {key}":
        raise HTTPException(401, "Invalid API key")


def send_webhook(url: str, payload: dict) -> None:
    try:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json", "User-Agent": "GraphMind/0.7"}, method="POST")
        with urllib.request.urlopen(request, timeout=10):
            pass
    except Exception:
        pass

@app.get("/", include_in_schema=False)
def frontend():
    return FileResponse(FRONTEND)

@app.get("/health")
def health():
    return {"status": "ok", "service": "graphmind", "version": "0.7.0"}

@app.get("/api/v1/knowledge/charts")
def chart_knowledge():
    return {"version": "1.0", "charts": CHART_KNOWLEDGE}

@app.get("/api/v1/knowledge/concepts")
def semantic_concepts():
    return {"version": "1.0", "concepts": SEMANTIC_TERMS}

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
        raise HTTPException(400, "No supported documents uploaded")
    from app.services.processor import process_file
    results = [process_file(path, prompt) if Path(path).suffix.lower() in IMAGE_EXTENSIONS else {"chart": {"chart_id": Path(path).stem, "source_file": Path(path).name, "metadata": {"source_path": path}}, "analysis_plan": {}, "chunks": [], "processing": {"status": "ingested", "supported": True}} for path in accepted]
    analysis = analyze_job(results, prompt)
    JOBS[job_id] = {"status": "completed", "prompt": prompt, "charts": results, "analysis": analysis, "webhook": None}
    return JobResponse(job_id=job_id, status="completed", files=len(accepted), prompt=prompt)

@app.get("/api/v1/jobs/{job_id}")
def get_job(job_id: str):
    job = get_job_or_404(job_id)
    return {"job_id": job_id, "status": job["status"], "charts": len(job["charts"]), "analysis_status": job["analysis"]["status"], "safe_to_answer": job["analysis"]["safe_to_answer"], "confidence": job["analysis"].get("confidence", 0.0)}

@app.get("/api/v1/jobs/{job_id}/results")
def get_results(job_id: str):
    job = get_job_or_404(job_id)
    return {"job_id": job_id, **job}

@app.get("/api/v1/jobs/{job_id}/analysis")
def get_analysis(job_id: str):
    return {"job_id": job_id, "analysis": get_job_or_404(job_id)["analysis"]}

@app.post("/api/v1/integrations/{job_id}/access", response_model=ApiAccessResponse)
def create_integration_access(job_id: str):
    get_job_or_404(job_id)
    key = DeliveryService.create_api_key()
    API_KEYS[job_id] = key
    return ApiAccessResponse(job_id=job_id, api_key=key, base_url=f"/api/v1/integrations/{job_id}", endpoints={"data":f"/api/v1/integrations/{job_id}/data","json":f"/api/v1/integrations/{job_id}/json","analysis":f"/api/v1/jobs/{job_id}/analysis","manifest":f"/api/v1/integrations/{job_id}/manifest","status":f"/api/v1/jobs/{job_id}"})

@app.get("/api/v1/integrations/{job_id}/data")
def integration_data(job_id: str, authorization: str | None = Header(default=None)):
    require_key(job_id, authorization)
    return {"job_id": job_id, "data": get_job_or_404(job_id)["charts"]}

@app.get("/api/v1/integrations/{job_id}/json")
def integration_json(job_id: str, authorization: str | None = Header(default=None)):
    require_key(job_id, authorization)
    return DeliveryService.public_payload(job_id, get_job_or_404(job_id))

@app.get("/api/v1/integrations/{job_id}/manifest")
def integration_manifest(job_id: str, authorization: str | None = Header(default=None)):
    require_key(job_id, authorization)
    return DeliveryService.manifest(job_id, get_job_or_404(job_id))

@app.get("/api/v1/integrations/{job_id}/json/download")
def download_json(job_id: str, authorization: str | None = Header(default=None)):
    require_key(job_id, authorization)
    payload = json.dumps(DeliveryService.public_payload(job_id, get_job_or_404(job_id)), ensure_ascii=False, indent=2).encode("utf-8")
    return Response(payload, media_type="application/json", headers={"Content-Disposition": f'attachment; filename="graphmind-{job_id}.json"'})

@app.post("/api/v1/integrations/{job_id}/webhook")
def configure_webhook(job_id: str, request: WebhookRequest, authorization: str | None = Header(default=None)):
    require_key(job_id, authorization)
    job = get_job_or_404(job_id)
    job["webhook"] = request.url
    threading.Thread(target=send_webhook, args=(request.url, DeliveryService.public_payload(job_id, job)), daemon=True).start()
    return {"job_id": job_id, "webhook": request.url, "status": "configured_and_test_sent"}

@app.post("/api/v1/integrations/{job_id}/share")
def create_share(job_id: str, authorization: str | None = Header(default=None)):
    require_key(job_id, authorization)
    get_job_or_404(job_id)
    token = secrets.token_urlsafe(24)
    SHARES[token] = job_id
    return {"share_id": token, "url": f"/share/{token}"}

@app.get("/share/{token}")
def get_share(token: str):
    job_id = SHARES.get(token)
    if not job_id:
        raise HTTPException(404, "Share link not found")
    return DeliveryService.public_payload(job_id, get_job_or_404(job_id))

@app.get("/api/v1/integrations/{job_id}/csv")
def download_csv(job_id: str, authorization: str | None = Header(default=None)):
    require_key(job_id, authorization)
    return Response(DeliveryService.csv_bytes(job_id, get_job_or_404(job_id)), media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="graphmind-{job_id}.csv"'})

@app.get("/api/v1/integrations/{job_id}/xlsx")
def download_xlsx(job_id: str, authorization: str | None = Header(default=None)):
    require_key(job_id, authorization)
    return Response(DeliveryService.xlsx_bytes(job_id, get_job_or_404(job_id)), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f'attachment; filename="graphmind-{job_id}.xlsx"'})

@app.get("/api/v1/integrations/{job_id}/pdf")
def download_pdf(job_id: str, authorization: str | None = Header(default=None)):
    require_key(job_id, authorization)
    return Response(DeliveryService.pdf_bytes(job_id, get_job_or_404(job_id)), media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="graphmind-{job_id}.pdf"'})

@app.get("/api/v1/integrations/{job_id}/package")
def download_package(job_id: str, authorization: str | None = Header(default=None)):
    require_key(job_id, authorization)
    return Response(DeliveryService.package_bytes(job_id, get_job_or_404(job_id)), media_type="application/zip", headers={"Content-Disposition": f'attachment; filename="graphmind-{job_id}.zip"'})

@app.get("/api/v1/integrations/{job_id}/openapi")
def integration_openapi(job_id: str, authorization: str | None = Header(default=None)):
    require_key(job_id, authorization)
    get_job_or_404(job_id)
    return {"name":"GraphMind Integration API","version":"1.2","authentication":"Bearer API key","endpoints":{"GET /data":"Structured chart knowledge","GET /json":"Complete JSON payload","GET /analysis":"Validated deterministic analysis","GET /json/download":"JSON file export","GET /manifest":"Delivery manifest","GET /csv":"CSV export","GET /xlsx":"Excel export","GET /pdf":"PDF report","GET /package":"Complete ZIP package","POST /webhook":"Configure and test webhook","POST /share":"Create share link"}}
