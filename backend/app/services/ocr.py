from __future__ import annotations

from pathlib import Path

import pytesseract
from PIL import Image


class OCRService:
    def extract_text(self, path: Path) -> str:
        with Image.open(path) as image:
            return pytesseract.image_to_string(image).strip()
