from pathlib import Path
from uuid import uuid4
import shutil
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

app = FastAPI(title="GraphMind API", version="0.2.0")
DATA_DIR = Path("data/jobs")
JOBS: dict[str, dict] = {}
SUPPORTED = {".png", ".jpg", ".jpeg", ".webp"}

class JobResponse(BaseModel):
    job_id: str
    status: str
    files: int
    prompt: str

@app.get("/health")
def health(): return {"status": "ok", "service": "graphmind"}

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
    JOBS[job_id] = {"status": "completed", "prompt": prompt, "charts": results}
    return JobResponse(job_id=job_id, status="completed", files=len(accepted), prompt=prompt)

@app.get("/api/v1/jobs/{job_id}")
def get_job(job_id: str):
    job = JOBS.get(job_id)
    if not job: raise HTTPException(404, "Job not found")
    return {"job_id": job_id, "status": job["status"], "charts": len(job["charts"])}

@app.get("/api/v1/jobs/{job_id}/results")
def get_results(job_id: str):
    job = JOBS.get(job_id)
    if not job: raise HTTPException(404, "Job not found")
    return {"job_id": job_id, **job}
