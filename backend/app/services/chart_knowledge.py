from __future__ import annotations

from typing import Any


CHART_KNOWLEDGE: dict[str, dict[str, Any]] = {
    "bar": {
        "description": "Categorical comparison represented by bar length or height.",
        "expected": ["categorical_x_axis", "numeric_y_axis", "bars"],
        "risks": ["truncated_axis", "stacked_series", "dual_axis", "3d_perspective"],
    },
    "line": {
        "description": "Ordered observations connected by lines, commonly used for trends over time.",
        "expected": ["ordered_x_axis", "numeric_y_axis", "connected_points"],
        "risks": ["missing_points", "multiple_series", "dual_axis", "nonlinear_scale"],
    },
    "pie": {
        "description": "Parts of a whole represented by slices; values are commonly proportions or percentages.",
        "expected": ["categories", "parts_of_whole"],
        "risks": ["missing_categories", "rounded_percentages", "3d_perspective"],
    },
    "scatter": {
        "description": "Pairs of numeric observations represented as points on two numeric axes.",
        "expected": ["numeric_x_axis", "numeric_y_axis", "points"],
        "risks": ["overplotting", "trendline_confusion", "log_scale"],
    },
    "area": {
        "description": "Trend chart with filled area beneath one or more lines.",
        "expected": ["ordered_x_axis", "numeric_y_axis", "filled_series"],
        "risks": ["stacked_series", "overlap", "dual_axis"],
    },
    "unknown": {
        "description": "Chart structure could not be identified reliably.",
        "expected": [],
        "risks": ["unknown_chart_geometry"],
    },
}

SEMANTIC_TERMS: dict[str, str] = {
    "yoy": "year_over_year",
    "year over year": "year_over_year",
    "qoq": "quarter_over_quarter",
    "quarter over quarter": "quarter_over_quarter",
    "mom": "month_over_month",
    "month over month": "month_over_month",
    "cagr": "compound_annual_growth_rate",
    "margin": "margin",
    "share": "share_of_total",
    "market share": "market_share",
    "revenue": "revenue",
    "sales": "sales",
    "growth": "growth_rate",
}


def chart_knowledge(chart_type: str) -> dict[str, Any]:
    return CHART_KNOWLEDGE.get(chart_type, CHART_KNOWLEDGE["unknown"])


def extract_semantics(text: str) -> list[str]:
    lower = text.lower()
    return sorted({meaning for term, meaning in SEMANTIC_TERMS.items() if term in lower})


def validate_chart_structure(chart: Any) -> dict[str, Any]:
    knowledge = chart_knowledge(chart.chart_type)
    checks: list[dict[str, Any]] = []

    has_ocr = bool(chart.metadata.get("ocr_text"))
    has_values = any(series.values for series in chart.series)
    checks.append({"name": "ocr_present", "passed": has_ocr})
    checks.append({"name": "structured_values_present", "passed": has_values})
    checks.append({"name": "chart_type_known", "passed": chart.chart_type != "unknown"})

    numeric_count = sum(len(series.values) for series in chart.series)
    checks.append({"name": "numeric_values_count", "passed": numeric_count > 0, "count": numeric_count})

    warnings: list[str] = []
    if chart.chart_type == "unknown":
        warnings.append("Chart type is not confidently identified.")
    if not has_values:
        warnings.append("No structured numeric values were extracted.")
    if chart.confidence < 0.70:
        warnings.append("Extraction confidence is below the safe-answer threshold.")

    score_parts = [check["passed"] for check in checks[:3]]
    if numeric_count > 0:
        score_parts.append(True)
    score = sum(score_parts) / len(score_parts)
    confidence = round(min(chart.confidence, score), 3)

    return {
        "confidence": confidence,
        "safe_to_answer": confidence >= 0.70 and numeric_count > 0 and chart.chart_type != "unknown",
        "knowledge": knowledge,
        "semantic_concepts": extract_semantics(f"{chart.title} {chart.semantic_summary} {chart.metadata.get('ocr_text', '')}"),
        "checks": checks,
        "warnings": warnings,
    }
