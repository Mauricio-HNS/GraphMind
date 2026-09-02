from fastapi import FastAPI, File, Form, UploadFile
from pydantic import BaseModel
from uuid import uuid4

app = FastAPI(
    title="GraphMind API",
    version="0.1.0",
    description="Chart intelligence preprocessing engine for AI/RAG systems.",
)


class JobResponse(BaseModel):
    job_id: str
    status: str
    files: int
    prompt: str


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/v1/jobs", response_model=JobResponse)
async def create_job(
    prompt: str = Form(...),
    files: list[UploadFile] = File(...),
) -> JobResponse:
    job_id = str(uuid4())

    # MVP: ingestion only. Processing workers will be added next.
    return JobResponse(
        job_id=job_id,
        status="queued",
        files=len(files),
        prompt=prompt,
    )


@app.get("/api/v1/jobs/{job_id}")
def get_job(job_id: str) -> dict[str, str]:
    return {"job_id": job_id, "status": "queued"}


@app.get("/api/v1/jobs/{job_id}/results")
def get_results(job_id: str) -> dict[str, object]:
    return {
        "job_id": job_id,
        "status": "not_processed",
        "charts": [],
    }
