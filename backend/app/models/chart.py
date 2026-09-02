from typing import Any

from pydantic import BaseModel, Field


class ChartRegion(BaseModel):
    id: str
    kind: str
    description: str = ""
    bbox: list[float] = Field(default_factory=list)
    text: str = ""
    confidence: float = 0.0


class ChartSeries(BaseModel):
    name: str
    unit: str | None = None
    values: list[dict[str, Any]] = Field(default_factory=list)
    confidence: float = 0.0


class ChartDocument(BaseModel):
    chart_id: str
    source_file: str
    chart_type: str = "unknown"
    title: str = ""
    x_axis: dict[str, Any] = Field(default_factory=dict)
    y_axis: dict[str, Any] = Field(default_factory=dict)
    series: list[ChartSeries] = Field(default_factory=list)
    regions: list[ChartRegion] = Field(default_factory=list)
    semantic_summary: str = ""
    confidence: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)
