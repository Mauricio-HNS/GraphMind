from __future__ import annotations

import hashlib
import secrets
from typing import Any


class DeliveryService:
    """Builds integration metadata for completed GraphMind jobs."""

    @staticmethod
    def create_api_key() -> str:
        return "gm_" + secrets.token_urlsafe(32)

    @staticmethod
    def public_payload(job_id: str, job: dict[str, Any]) -> dict[str, Any]:
        return {
            "job_id": job_id,
            "status": job.get("status"),
            "prompt": job.get("prompt"),
            "charts": job.get("charts", []),
        }

    @staticmethod
    def manifest(job_id: str, job: dict[str, Any]) -> dict[str, Any]:
        payload = DeliveryService.public_payload(job_id, job)
        raw = repr(payload).encode("utf-8")
        return {
            "format": "graphmind.delivery.v1",
            "job_id": job_id,
            "files": len(job.get("charts", [])),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "endpoints": {
                "status": f"/api/v1/jobs/{job_id}",
                "results": f"/api/v1/jobs/{job_id}/results",
                "data": f"/api/v1/integrations/{job_id}/data",
                "manifest": f"/api/v1/integrations/{job_id}/manifest",
            },
        }
