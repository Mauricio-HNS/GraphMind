from __future__ import annotations

from pathlib import Path
from typing import Protocol

from app.models.chart import ChartDocument, ChartRegion


class ChartExtractor(Protocol):
    def extract(self, path: Path) -> ChartDocument:
        ...


class BasicImageExtractor:
    """Dependency-light first extractor.

    It establishes the visual-processing contract without pretending to recover
    chart values before OCR/VLM adapters are connected.
    """

    SUPPORTED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}

    def extract(self, path: Path) -> ChartDocument:
        chart_id = path.stem
        document = ChartDocument(
            chart_id=chart_id,
            source_file=path.name,
            metadata={"source_path": str(path)},
        )

        if path.suffix.lower() in self.SUPPORTED_IMAGE_EXTENSIONS:
            document.regions.append(
                ChartRegion(
                    id=f"{chart_id}:full",
                    kind="full_chart",
                    description="Original chart image. Awaiting OCR/VLM extraction.",
                    bbox=[0, 0, 1, 1],
                    confidence=1.0,
                )
            )

        return document
