from typing import Any


class AnalysisPlan(dict[str, Any]):
    pass


def build_analysis_plan(prompt: str) -> AnalysisPlan:
    """Create a deterministic initial analysis contract from the user intent.

    This is intentionally lightweight in the first MVP. A model-backed planner
    can replace it later without changing the API contract.
    """
    normalized = prompt.strip()

    operations: list[str] = []
    lowered = normalized.lower()

    if any(word in lowered for word in ("compar", "compare", "diferen", "difference")):
        operations.append("comparison")
    if any(word in lowered for word in ("crescimento", "growth", "evolu", "trend", "tend")):
        operations.append("trend")
    if any(word in lowered for word in ("maior", "menor", "ranking", "top", "highest", "lowest")):
        operations.append("ranking")
    if any(word in lowered for word in ("anomalia", "anomaly", "outlier")):
        operations.append("anomaly_detection")

    return AnalysisPlan(
        objective=normalized,
        operations=operations,
        metrics=[],
        dimensions=[],
        filters=[],
        ignore=[],
    )
