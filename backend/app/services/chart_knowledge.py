from __future__ import annotations

from typing import Any

CHART_KNOWLEDGE: dict[str, dict[str, Any]] = {
    "bar": {"description": "Categorical comparison represented by bar length or height.", "expected": ["categorical_x_axis", "numeric_y_axis", "bars"], "risks": ["truncated_axis", "stacked_series", "dual_axis", "3d_perspective"]},
    "line": {"description": "Ordered observations connected by lines, commonly used for trends over time.", "expected": ["ordered_x_axis", "numeric_y_axis", "connected_points"], "risks": ["missing_points", "multiple_series", "dual_axis", "nonlinear_scale"]},
    "pie": {"description": "Parts of a whole represented by slices; values are commonly proportions or percentages.", "expected": ["categories", "parts_of_whole"], "risks": ["missing_categories", "rounded_percentages", "3d_perspective"]},
    "scatter": {"description": "Pairs of numeric observations represented as points on two numeric axes.", "expected": ["numeric_x_axis", "numeric_y_axis", "points"], "risks": ["overplotting", "trendline_confusion", "log_scale"]},
    "area": {"description": "Trend chart with filled area beneath one or more lines.", "expected": ["ordered_x_axis", "numeric_y_axis", "filled_series"], "risks": ["stacked_series", "overlap", "dual_axis"]},
    "unknown": {"description": "Chart structure could not be identified reliably.", "expected": [], "risks": ["unknown_chart_geometry"]},
}

SEMANTIC_TERMS: dict[str, str] = {
    "yoy": "year_over_year", "year over year": "year_over_year", "ano contra ano": "year_over_year",
    "qoq": "quarter_over_quarter", "quarter over quarter": "quarter_over_quarter",
    "mom": "month_over_month", "month over month": "month_over_month", "mês contra mês": "month_over_month",
    "cagr": "compound_annual_growth_rate", "margin": "margin", "margem": "margin",
    "share": "share_of_total", "market share": "market_share", "participação de mercado": "market_share",
    "revenue": "revenue", "sales": "sales", "growth": "growth_rate", "crescimento": "growth_rate",
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
    numeric_count = sum(len(series.values) for series in chart.series)

    checks.extend([
        {"name": "ocr_present", "passed": has_ocr},
        {"name": "structured_values_present", "passed": has_values},
        {"name": "chart_type_known", "passed": chart.chart_type != "unknown"},
        {"name": "numeric_values_count", "passed": numeric_count > 0, "count": numeric_count},
    ])

    warnings: list[str] = []
    if chart.chart_type == "unknown":
        warnings.append("Chart type is not confidently identified.")
    if not has_values:
        warnings.append("No structured numeric values were extracted.")
    if chart.metadata.get("extraction", {}).get("method") == "ocr_heuristic":
        warnings.append("Values come from OCR heuristics and have not been visually cross-validated.")
    for risk in knowledge["risks"]:
        if risk in {"dual_axis", "nonlinear_scale", "log_scale", "truncated_axis", "3d_perspective"}:
            warnings.append(f"Potential risk requiring visual validation: {risk}.")

    # OCR-only extraction is deliberately never marked safe. A safe answer requires
    # independent visual/geometric evidence or trusted source data in a later stage.
    method = chart.metadata.get("extraction", {}).get("method", "")
    independent_validation = bool(chart.metadata.get("visual_validation", {}).get("independent"))
    source_verified = bool(chart.metadata.get("source_data", {}).get("verified"))
    base = 0.0
    if has_ocr: base += 0.15
    if has_values: base += 0.20
    if chart.chart_type != "unknown": base += 0.15
    if numeric_count >= 2: base += 0.10
    if independent_validation: base += 0.25
    if source_verified: base += 0.25
    if method == "ocr_heuristic": base = min(base, 0.65)

    confidence = round(min(max(base, chart.confidence), 0.99), 3)
    safe = confidence >= 0.80 and (independent_validation or source_verified) and numeric_count > 0
    return {
        "confidence": confidence,
        "safe_to_answer": safe,
        "knowledge": knowledge,
        "semantic_concepts": extract_semantics(f"{chart.title} {chart.semantic_summary} {chart.metadata.get('ocr_text', '')}"),
        "checks": checks,
        "warnings": warnings,
        "evidence_policy": "Require independent visual/geometric validation or verified source data before asserting numeric facts.",
    }
