# GraphMind

GraphMind is a chart intelligence engine that transforms batches of charts into structured, AI-ready knowledge.

## Vision

Upload one chart or hundreds of charts, describe what you want to discover, and let GraphMind prepare the visual information for downstream AI analysis.

## Pipeline

```text
UPLOAD
  ↓
INGESTION
  ↓
CHART PROCESSING
  ├─ chart detection
  ├─ OCR
  ├─ layout detection
  ├─ title / axes / legends
  └─ series / values
  ↓
INTELLIGENT FATIAMENTO
  ├─ spatial regions
  ├─ semantic chunks
  └─ retrieval chunks
  ↓
NORMALIZATION
  ├─ structured JSON
  ├─ Markdown representation
  └─ metadata + confidence
  ↓
PROMPT / ANALYSIS PLANNER
  ↓
RAG + STRUCTURED DATA
  ↓
LLM / AGENT
```

## Core principle

GraphMind must not rely only on image embeddings. Numerical questions should be answered from structured chart data whenever possible, while the original image and extracted regions remain available for traceability.

## Initial API

- `GET /health`
- `POST /api/v1/jobs`
- `GET /api/v1/jobs/{job_id}`
- `GET /api/v1/jobs/{job_id}/results`

## Project status

Early MVP. The repository currently contains the initial architecture and API skeleton.
