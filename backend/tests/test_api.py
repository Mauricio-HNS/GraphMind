import io
import sys
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.main import app, API_KEYS, JOBS, SHARES  # noqa: E402

client = TestClient(app)


def setup_function():
    JOBS.clear()
    API_KEYS.clear()
    SHARES.clear()


def png_bytes() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (20, 20), "white").save(buffer, format="PNG")
    return buffer.getvalue()


def create_job():
    response = client.post(
        "/api/v1/jobs",
        data={"prompt": "Compare trends and identify anomalies"},
        files={"files": ("chart.png", png_bytes(), "image/png")},
    )
    assert response.status_code == 200
    return response.json()["job_id"]


def get_key(job_id):
    response = client.post(f"/api/v1/integrations/{job_id}/access")
    assert response.status_code == 200
    return response.json()["api_key"]


def auth(key):
    return {"Authorization": f"Bearer {key}"}


def test_health_and_job_flow():
    assert client.get("/health").json()["status"] == "ok"
    job_id = create_job()
    assert client.get(f"/api/v1/jobs/{job_id}").status_code == 200
    assert client.get(f"/api/v1/jobs/{job_id}/results").status_code == 200


def test_protected_integration_endpoints():
    job_id = create_job()
    assert client.get(f"/api/v1/integrations/{job_id}/json").status_code == 404
    key = get_key(job_id)
    headers = auth(key)
    for endpoint in ("data", "json", "manifest", "json/download", "openapi"):
        response = client.get(f"/api/v1/integrations/{job_id}/{endpoint}", headers=headers)
        assert response.status_code == 200, (endpoint, response.text)


def test_export_formats():
    job_id = create_job()
    headers = auth(get_key(job_id))
    expectations = {
        "csv": "text/csv",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "pdf": "application/pdf",
        "package": "application/zip",
    }
    for endpoint, content_type in expectations.items():
        response = client.get(f"/api/v1/integrations/{job_id}/{endpoint}", headers=headers)
        assert response.status_code == 200
        assert response.headers["content-type"].startswith(content_type)
        assert len(response.content) > 0
        assert "attachment" in response.headers.get("content-disposition", "")

    json_download = client.get(f"/api/v1/integrations/{job_id}/json/download", headers=headers)
    assert json_download.status_code == 200
    assert "attachment" in json_download.headers["content-disposition"]
    assert json_download.json()["job_id"] == job_id


def test_share_link_and_webhook_configuration():
    job_id = create_job()
    headers = auth(get_key(job_id))
    share = client.post(f"/api/v1/integrations/{job_id}/share", headers=headers)
    assert share.status_code == 200
    token = share.json()["share_id"]
    public = client.get(f"/share/{token}")
    assert public.status_code == 200
    assert public.json()["job_id"] == job_id

    webhook = client.post(
        f"/api/v1/integrations/{job_id}/webhook",
        headers={**headers, "Content-Type": "application/json"},
        json={"url": "http://127.0.0.1:1/test"},
    )
    assert webhook.status_code == 200
    assert webhook.json()["status"] == "configured_and_test_sent"
