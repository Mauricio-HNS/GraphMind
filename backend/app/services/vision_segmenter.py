from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from app.models.chart import ChartRegion


@dataclass
class Segment:
    kind: str
    bbox: list[float]


class VisionSegmenter:
    """First visual segmentation layer for chart images.

    Coordinates are normalized to 0..1 so downstream OCR/VLM providers can use
    the same contract regardless of image resolution.
    """

    def segment(self, path: Path) -> list[ChartRegion]:
        with Image.open(path) as image:
            width, height = image.size

        regions = [
            ChartRegion(
                id=f"{path.stem}:full",
                kind="full_chart",
                description="Complete original chart",
                bbox=[0.0, 0.0, 1.0, 1.0],
                confidence=1.0,
            )
        ]

        image = cv2.imread(str(path))
        if image is None:
            return regions

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        _, threshold = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 5))
        merged = cv2.morphologyEx(threshold, cv2.MORPH_CLOSE, kernel)
        contours, _ = cv2.findContours(merged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        candidates: list[tuple[int, int, int, int]] = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            if w * h < (width * height * 0.002):
                continue
            candidates.append((x, y, w, h))

        candidates.sort(key=lambda item: item[1])
        for index, (x, y, w, h) in enumerate(candidates[:20]):
            bbox = [x / width, y / height, w / width, h / height]
            regions.append(
                ChartRegion(
                    id=f"{path.stem}:region:{index}",
                    kind="visual_region",
                    description="Candidate chart region detected from image layout",
                    bbox=[round(value, 6) for value in bbox],
                    confidence=0.55,
                )
            )

        return regions
