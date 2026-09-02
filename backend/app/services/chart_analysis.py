from __future__ import annotations

from statistics import mean
from typing import Any


def _values(chart: dict[str, Any]) -> list[tuple[str, float]]:
    result: list[tuple[str, float]] = []
    for series in chart.get("series", []):
        for item in series.get("values", []):
            value = item.get("value")
            if isinstance(value, (int, float)) and item.get("value") is not None:
                result.append((str(item.get("dimension", "value")), float(value)))
    return result


def _requested(prompt: str) -> list[str]:
    lower = prompt.lower()
    requested: list[str] = []
    groups = {
        "comparison": ("compare", "comparison", "comparar", "comparação", "diferença"),
        "trend": ("trend", "tendência", "evolution", "evolução", "growth", "crescimento"),
        "ranking": ("rank", "ranking", "maior", "menor", "highest", "lowest", "top"),
        "anomaly": ("anomaly", "anomal", "outlier", "anomalia"),
    }
    for name, words in groups.items():
        if any(word in lower for word in words):
            requested.append(name)
    return requested or ["summary"]


def analyze_chart(chart: dict[str, Any], prompt: str) -> dict[str, Any]:
    validation = chart.get("metadata", {}).get("knowledge_validation", {})
    values = _values(chart)
    requested = _requested(prompt)
    evidence = [
        {"chart_id": chart.get("chart_id"), "source_file": chart.get("source_file"), "series": s.get("name"), "values": s.get("values", [])}
        for s in chart.get("series", []) if s.get("values")
    ]
    result: dict[str, Any] = {
        "status": "validated" if validation.get("safe_to_answer") else "needs_review",
        "safe_to_answer": bool(validation.get("safe_to_answer")),
        "confidence": validation.get("confidence", chart.get("confidence", 0.0)),
        "requested_operations": requested,
        "semantic_concepts": validation.get("semantic_concepts", []),
        "findings": [],
        "evidence": evidence,
        "warnings": validation.get("warnings", []),
    }
    if not values:
        result["findings"].append("No structured numeric values are available for a reliable calculation.")
        return result

    nums = [value for _, value in values]
    if "summary" in requested:
        result["findings"].extend([
            {"metric": "count", "value": len(nums)},
            {"metric": "minimum", "value": min(nums)},
            {"metric": "maximum", "value": max(nums)},
            {"metric": "average", "value": mean(nums)},
        ])
    if "trend" in requested and len(nums) >= 2:
        first, last = nums[0], nums[-1]
        change = last - first
        pct = None if first == 0 else (change / abs(first)) * 100
        result["findings"].append({"metric": "change", "from": first, "to": last, "absolute": change, "percent": pct})
    if "ranking" in requested:
        result["findings"].append({"metric": "ranking", "values": [{"dimension": d, "value": v} for d, v in sorted(values, key=lambda pair: pair[1], reverse=True)]})
    if "comparison" in requested and len(nums) >= 2:
        result["findings"].append({"metric": "range", "minimum": min(nums), "maximum": max(nums), "difference": max(nums) - min(nums)})
    if "anomaly" in requested and len(nums) >= 4:
        avg = mean(nums)
        deviations = [(d, v, abs(v - avg)) for d, v in values]
        avg_dev = mean([d for _, _, d in deviations])
        threshold = 2 * (avg_dev or 1)
        result["findings"].append({"metric": "anomalies", "values": [{"dimension": d, "value": v} for d, v, deviation in deviations if deviation > threshold], "method": "mean_deviation_heuristic"})
    return result


def analyze_job(charts: list[dict[str, Any]], prompt: str) -> dict[str, Any]:
    analyses = [analyze_chart(item.get("chart", {}), prompt) for item in charts]
    safe = bool(analyses) and all(item["safe_to_answer"] for item in analyses)
    confidences = [float(item.get("confidence", 0.0)) for item in analyses]
    return {
        "safe_to_answer": safe,
        "status": "validated" if safe else "needs_review",
        "confidence": round(min(confidences), 3) if confidences else 0.0,
        "prompt": prompt,
        "charts": analyses,
        "guardrails": {
            "numeric_assertions_require_validation": True,
            "llm_must_not_invent_values": True,
            "low_confidence_behavior": "return_needs_review",
        },
        "note": "Deterministic calculations use extracted structured values. An LLM may interpret validated findings, but must not invent source values or override validation warnings.",
    }
