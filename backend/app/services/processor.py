from pathlib import Path
from uuid import uuid4

from app.models.chart import ChartDocument
from app.services.chunker import build_retrieval_chunks
from app.services.prompt_planner import build_analysis_plan


SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".pdf"}


def process_file(path: str, prompt: str) -> dict:
    """Build the processing envelope for one uploaded chart/document.

    Actual OCR/vision extraction is deliberately isolated from this contract.
    This lets us plug in OpenCV, OCR, VLMs or external chart extractors later.
    """
    source = Path(path)
    chart = ChartDocument(
        chart_id=str(uuid4()),
        source_file=source.name,
        metadata={"extension": source.suffix.lower()},
    )

    return {
        "chart": chart.model_dump(),
        "analysis_plan": build_analysis_plan(prompt),
        "chunks": build_retrieval_chunks(chart),
        "processing": {
            "status": "awaiting_visual_extraction",
            "supported": source.suffix.lower() in SUPPORTED_EXTENSIONS,
        },
    }
