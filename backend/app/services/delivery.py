from __future__ import annotations

import csv
import hashlib
import io
import json
import secrets
import zipfile
from typing import Any


class DeliveryService:
    """Creates deterministic, exportable delivery artifacts for GraphMind jobs."""

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
        raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
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

    @staticmethod
    def csv_bytes(job_id: str, job: dict[str, Any]) -> bytes:
        out = io.StringIO()
        writer = csv.writer(out)
        writer.writerow(["job_id", "chart_id", "source_file", "chart_type", "series", "dimension", "value", "unit", "confidence"])
        for item in job.get("charts", []):
            chart = item.get("chart", {})
            for series in chart.get("series", []):
                for point in series.get("values", []):
                    dimension = point.get("x", point.get("label", point.get("dimension", "")))
                    value = point.get("y", point.get("value", point.get("v", "")))
                    writer.writerow([job_id, chart.get("chart_id", ""), chart.get("source_file", ""), chart.get("chart_type", "unknown"), series.get("name", ""), dimension, value, series.get("unit", ""), series.get("confidence", 0)])
        return out.getvalue().encode("utf-8-sig")

    @staticmethod
    def xlsx_bytes(job_id: str, job: dict[str, Any]) -> bytes:
        from openpyxl import Workbook
        wb = Workbook()
        ws = wb.active
        ws.title = "Chart Data"
        ws.append(["job_id", "chart_id", "source_file", "chart_type", "series", "dimension", "value", "unit", "confidence"])
        for item in job.get("charts", []):
            chart = item.get("chart", {})
            for series in chart.get("series", []):
                for point in series.get("values", []):
                    ws.append([job_id, chart.get("chart_id", ""), chart.get("source_file", ""), chart.get("chart_type", "unknown"), series.get("name", ""), point.get("x", point.get("label", point.get("dimension", ""))), point.get("y", point.get("value", point.get("v", ""))), series.get("unit", ""), series.get("confidence", 0)])
        meta = wb.create_sheet("Metadata")
        meta.append(["Field", "Value"])
        meta.append(["Job ID", job_id])
        meta.append(["Prompt", job.get("prompt", "")])
        meta.append(["Status", job.get("status", "")])
        buffer = io.BytesIO()
        wb.save(buffer)
        return buffer.getvalue()

    @staticmethod
    def pdf_bytes(job_id: str, job: dict[str, Any]) -> bytes:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
        from reportlab.lib import colors

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
        styles = getSampleStyleSheet()
        story = [Paragraph("GraphMind Analysis Report", styles["Title"]), Spacer(1, 12), Paragraph(f"Job: {job_id}", styles["Normal"]), Paragraph(f"Objective: {job.get('prompt', '')}", styles["Normal"]), Spacer(1, 18)]
        for item in job.get("charts", []):
            chart = item.get("chart", {})
            story.append(Paragraph(chart.get("title") or chart.get("source_file", "Chart"), styles["Heading2"]))
            story.append(Paragraph(f"Type: {chart.get('chart_type', 'unknown')} | Confidence: {chart.get('confidence', 0)}", styles["Normal"]))
            if chart.get("semantic_summary"):
                story.append(Paragraph(chart["semantic_summary"], styles["BodyText"]))
            rows = [["Series", "Dimension", "Value", "Unit"]]
            for series in chart.get("series", []):
                for point in series.get("values", []):
                    rows.append([series.get("name", ""), point.get("x", point.get("label", "")), str(point.get("y", point.get("value", ""))), str(series.get("unit", ""))])
            if len(rows) > 1:
                table = Table(rows[:101], repeatRows=1)
                table.setStyle(TableStyle([("GRID", (0,0), (-1,-1), 0.4, colors.grey), ("BACKGROUND", (0,0), (-1,0), colors.lightgrey)]))
                story.extend([Spacer(1, 8), table])
            story.append(Spacer(1, 18))
        doc.build(story)
        return buffer.getvalue()

    @staticmethod
    def package_bytes(job_id: str, job: dict[str, Any]) -> bytes:
        payload = DeliveryService.public_payload(job_id, job)
        manifest = DeliveryService.manifest(job_id, job)
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("graphmind.json", json.dumps(payload, ensure_ascii=False, indent=2))
            archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
            archive.writestr("data.csv", DeliveryService.csv_bytes(job_id, job))
            archive.writestr("report.pdf", DeliveryService.pdf_bytes(job_id, job))
        return buffer.getvalue()
