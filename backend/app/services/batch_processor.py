from __future__ import annotations

from pathlib import Path
from typing import Any

from app.services.processor import process_file


class BatchProcessor:
    """Processes an arbitrary collection of chart files independently."""

    def process(self, files: list[Path], prompt: str) -> dict[str, Any]:
        results: list[dict[str, Any]] = []
        for path in files:
            results.append(process_file(path, prompt))

        return {
            "total_files": len(files),
            "prompt": prompt,
            "charts": results,
        }
