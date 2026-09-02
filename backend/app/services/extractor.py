from __future__ import annotations

from pathlib import Path
from typing import Protocol

from app.models.chart import ChartDocument
from app.services.chart_parser import parse_ocr
from app.services.ocr import OCRService
from app.services.vision_segmenter import VisionSegmenter


class ChartExtractor(Protocol):
    def extract(self, path: Path) -> ChartDocument:
        ...


class BasicImageExtractor:
    SUPPORTED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}

    def __init__(self) -> None:
        self.segmenter = VisionSegmenter()
        self.ocr = OCRService()

    def extract(self, path: Path) -> ChartDocument:
        chart_id = path.stem
        document = ChartDocument(
            chart_id=chart_id,
            source_file=path.name,
            metadata={"source_path": str(path)},
        )

        if path.suffix.lower() not in self.SUPPORTED_IMAGE_EXTENSIONS:
            return document

        document.regions = self.segmenter.segment(path)
        ocr_text = self.ocr.extract_text(path)
        document.metadata["ocr_text"] = ocr_text
        document = parse_ocr(document, ocr_text)
        document.metadata["processing_stage"] = "ocr_visual_segmentation_and_structured_extraction"
        return document
