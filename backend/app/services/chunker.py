from typing import Any

from app.models.chart import ChartDocument


def build_retrieval_chunks(chart: ChartDocument) -> list[dict[str, Any]]:
    """Convert a normalized chart into small semantic units suitable for RAG.

    Spatial crops are represented by region references; numeric values remain
    structured rather than being flattened into prose only.
    """
    chunks: list[dict[str, Any]] = []

    chunks.append(
        {
            "chunk_type": "chart",
            "chart_id": chart.chart_id,
            "text": chart.semantic_summary or chart.title,
            "metadata": {"source_file": chart.source_file, "chart_type": chart.chart_type},
        }
    )

    if chart.title:
        chunks.append(
            {
                "chunk_type": "title",
                "chart_id": chart.chart_id,
                "text": chart.title,
                "metadata": {"source_file": chart.source_file},
            }
        )

    for series in chart.series:
        chunks.append(
            {
                "chunk_type": "series",
                "chart_id": chart.chart_id,
                "text": series.name,
                "data": series.values,
                "metadata": {"unit": series.unit, "confidence": series.confidence},
            }
        )

    for region in chart.regions:
        chunks.append(
            {
                "chunk_type": "region",
                "chart_id": chart.chart_id,
                "region_id": region.id,
                "text": region.text or region.description,
                "bbox": region.bbox,
                "metadata": {"kind": region.kind, "confidence": region.confidence},
            }
        )

    return chunks
