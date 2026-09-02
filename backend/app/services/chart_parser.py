from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from app.models.chart import ChartDocument, ChartSeries


NUMBER_RE = re.compile(r"(?<![\w])[-+]?\d+(?:[.,]\d+)?(?:\s?[%€$£]|\s?million|\s?billion)?(?![\w])", re.I)


def _number(value: str) -> float | None:
    raw = value.strip().lower().replace(" ", "")
    raw = raw.replace("€", "").replace("$", "").replace("£", "").replace("%", "")
    if raw.endswith("million"):
        raw = raw[:-7]
        multiplier = 1_000_000
    elif raw.endswith("billion"):
        raw = raw[:-7]
        multiplier = 1_000_000_000
    else:
        multiplier = 1
    if "," in raw and "." in raw:
        raw = raw.replace(",", "")
    else:
        raw = raw.replace(",", ".")
    try:
        return float(raw) * multiplier
    except ValueError:
        return None


def infer_chart_type(text: str) -> str:
    lower = text.lower()
    patterns = {
        "bar": ("bar chart", "bar graph", "barra", "barras"),
        "line": ("line chart", "line graph", "linha", "linhas"),
        "pie": ("pie chart", "pie graph", "pizza", "donut", "doughnut"),
        "scatter": ("scatter", "dispersão", "dispersao"),
        "area": ("area chart", "area graph"),
    }
    for kind, terms in patterns.items():
        if any(term in lower for term in terms):
            return kind
    return "unknown"


def parse_ocr(chart: ChartDocument, ocr_text: str) -> ChartDocument:
    lines = [line.strip() for line in ocr_text.splitlines() if line.strip()]
    chart.chart_type = infer_chart_type(ocr_text)
    chart.title = lines[0][:300] if lines else ""
    chart.metadata["ocr_lines"] = lines

    matches: list[dict[str, Any]] = []
    for index, token in enumerate(NUMBER_RE.findall(ocr_text)):
        value = _number(token)
        if value is None:
            continue
        matches.append({"dimension": f"value_{index + 1}", "value": value, "raw": token})

    if matches:
        chart.series = [
            ChartSeries(
                name="OCR extracted values",
                values=matches,
                confidence=0.45,
            )
        ]

    chart.confidence = 0.55 if ocr_text else 0.15
    chart.metadata["extraction"] = {
        "method": "ocr_heuristic",
        "numeric_values": len(matches),
        "chart_type_inferred": chart.chart_type != "unknown",
    }
    return chart
