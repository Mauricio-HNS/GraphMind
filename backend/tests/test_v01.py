from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image, ImageDraw

from app.main import app


def chart_png() -> bytes:
    image = Image.new("RGB", (900, 500), "white")
    draw = ImageDraw.Draw(image)
    draw.text((40, 30), "Sales by Region", fill="black")
    draw.text((80, 420), "Madrid 120", fill="black")
    draw.text((330, 420), "Barcelona 95", fill="black")
    draw.text((600, 420), "Valencia 80", fill="black")
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_v01_end_to_end_exports_and_share():
    client = TestClient(app)
    response = client.post(
        "/api/v1/jobs",
        data={"prompt": "Compare sales and identify anomalies."},
        files={"files": ("sales.png", chart_png(), "image/png")},
    )
    assert response.status_code == 200
    job_id = response.json()["job_id"]

    access = client.post(f"/api/v1/integrations/{job_id}/access")
    assert access.status_code == 200
    key = access.json()["api_key"]
    headers = {"Authorization": f"Bearer {key}"}

    assert client.get(f"/api/v1/integrations/{job_id}/json", headers=headers).status_code == 200
    assert client.get(f"/api/v1/integrations/{job_id}/json/download", headers=headers).headers["content-type"].startswith("application/json")
    assert client.get(f"/api/v1/integrations/{job_id}/manifest", headers=headers).status_code == 200
    assert client.get(f"/api/v1/integrations/{job_id}/csv", headers=headers).headers["content-type"].startswith("text/csv")
    assert client.get(f"/api/v1/integrations/{job_id}/xlsx", headers=headers).headers["content-type"].startswith("application/vnd.openxmlformats")
    assert client.get(f"/api/v1/integrations/{job_id}/pdf", headers=headers).headers["content-type"].startswith("application/pdf")
    assert client.get(f"/api/v1/integrations/{job_id}/package", headers=headers).headers["content-type"].startswith("application/zip")

    share = client.post(f"/api/v1/integrations/{job_id}/share", headers=headers)
    assert share.status_code == 200
    token = share.json()["share_id"]
    public = client.get(f"/share/{token}")
    assert public.status_code == 200
    assert public.json()["job_id"] == job_id


def test_invalid_api_key_is_rejected():
    client = TestClient(app)
    response = client.get("/api/v1/integrations/not-a-job/data", headers={"Authorization": "Bearer bad"})
    assert response.status_code == 404
