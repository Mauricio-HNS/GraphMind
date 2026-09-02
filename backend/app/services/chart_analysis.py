from __future__ import annotations

from statistics import mean
from typing import Any


def _values(chart: dict[str, Any]) -> list[tuple[str, float]]:
    result: list[tuple[str, float]] = []
    for series in chart.get("series", []):
        for item in series.get("values", []):
            value = item.get("value")
            if isinstance(value, (int, float)):
                result.append((str(item.get("dimension", "value")), float(value)))
    return result


def analyze_chart(chart: dict[str, Any], prompt: str) -> dict[str, Any]:
    validation = chart.get("metadata", {}).get("knowledge_validation", {})
    values = _values(chart)
    lower = prompt.lower()
    requested: list[str] = []
    if any(word in lower for word in ("compare", "comparison", "comparar", "comparação")):
        requested.append("comparison")
    if any(word in lower for word in ("trend", "tendência", "evolution", "evolução", "growth", "crescimento")):
        requested.append("trend")
    if any(word in lower for word in ("rank", "ranking", "maior", "menor", "highest", "lowest")):
        requested.append("ranking")
    if any(word in lower for word in ("anomaly", "anomal", "outlier", "anomalia")):
        requested.append("anomaly")
    if not requested:
        requested = ["summary"]

    evidence = [{"chart_id": chart.get("chart_id"), "source_file": chart.get("source_file"), "series": s.get("name"), "values": s.get("values", [])} for s in chart.get("series", []) if s.get("values")]
    result: dict[str, Any] = {
        "status": "validated" if validation.get("safe_to_answer") else "needs_review",
        "safe_to_answer": bool(validation.get("safe_to_answer")),
        "confidence": validation.get("confidence", chart.get("confidence", 0.0)),
        "requested_operations": requested,
        "findings": [],
        "evidence": evidence,
        "warnings": validation.get("warnings", []),
    }

    if not values:
        result["findings"].append("No structured numeric values are available for a reliable calculation.")
        return result

    nums = [value for _, value in values]
    if "summary" in requested:
        result["findings"].append({"metric": "count", "value": len(nums)})
        result["findings"].append({"metric": "minimum", "value": min(nums)})
        result["findings"].append({"metric": "maximum", "value": max(nums)})
        result["findings"].append({"metric": "average", "value": mean(nums)})

    if "trend" in requested and len(nums) >= 2:
        first, last = nums[0], nums[-1]
        change = last - first
        pct = None if first == 0 else (change / abs(first)) * 100
        result["findings"].append({"metric": "change", "from": first, "to": last, "absolute": change, "percent": pct})

    if "ranking" in requested:
        result["findings"].append({"metric": "ranking", "values": [{"dimension": d, "value": v} for d, v in sorted(values, key=lambda pair: pair[1], reverse=True)]})

    if "comparison" in requested and len(nums) >= 2:
        result["findings"].append({"metric": "pairwise_range", "minimum": min(nums), "maximum": max(nums), "difference": max(nums) - min(nums)})

    if "anomaly" in requested and len(nums) >= 4:
        avg = mean(nums)
        deviations = [(d, v, abs(v - avg)) for d, v in values]
        threshold = 2 * (mean([d for _, _, d in deviations]) or 1)
        outliers = [{"dimension": d, "value": v} for d, v, deviation in deviations if deviation > threshold]
        result["findings"].append({"metric": "anomalies", "values": outliers, "method": "mean_deviation_heuristic"})

    return result


def analyze_job(charts: list[dict[str, Any]], prompt: str) -> dict[str, Any]:
    analyses = [analyze_chart(item.get("chart", {}), prompt) for item in charts]
    safe = all(item["safe_to_answer"] for item in analyses) if analyses else False
    return {
        "safe_to_answer": safe,
        "status": "validated" if safe else "needs_review",
        "prompt": prompt,
        "charts": analyses,
        "note": "Deterministic calculations are performed from extracted structured values. An LLM should only interpret validated findings, not invent source values.",
    }
