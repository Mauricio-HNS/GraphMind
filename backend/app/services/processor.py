from pathlib import Path
from uuid import uuid4

from app.models.chart import ChartDocument
from app.services.chunker import build_retrieval_chunks
from app.services.extractor import BasicImageExtractor
from app.services.prompt_planner import build_analysis_plan


SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".pdf"}


def process_file(path: str, prompt: str) -> dict:
    """Process one chart while keeping extraction replaceable."""
    source = Path(path)
    extension = source.suffix.lower()

    if extension in BasicImageExtractor.SUPPORTED_IMAGE_EXTENSIONS:
        chart = BasicImageExtractor().extract(source)
    else:
        chart = ChartDocument(
            chart_id=str(uuid4()),
            source_file=source.name,
            metadata={"extension": extension},
        )

    plan = build_analysis_plan(prompt)
    chunks = build_retrieval_chunks(chart)

    return {
        "chart": chart.model_dump(),
        "analysis_plan": plan,
        "chunks": chunks,
        "processing": {
            "status": "awaiting_ocr_and_vlm" if extension in SUPPORTED_EXTENSIONS else "unsupported",
            "supported": extension in SUPPORTED_EXTENSIONS,
        },
    }
