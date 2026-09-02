# GraphMind

GraphMind is a chart intelligence engine that transforms batches of charts into structured, AI-ready knowledge.

## Vision

Upload one chart or hundreds of charts, describe what you want to discover, and let GraphMind prepare visual information for downstream AI analysis.

## Pipeline

```text
UPLOAD → INGESTION → CHART PROCESSING → INTELLIGENT FATIAMENTO
       → NORMALIZATION → ANALYSIS PLAN → RAG / STRUCTURED DATA → LLM / AGENT
```

## Delivery layer

After an analysis, GraphMind can expose the result to external systems instead of forcing the user to download it manually.

Current integration contract:

- REST integration access with per-job Bearer API key
- Structured JSON endpoint
- Structured data endpoint
- Delivery manifest with SHA-256 checksum
- Webhook configuration endpoint
- Integration OpenAPI metadata
- Frontend delivery selector for API, software, AI/agents, data, webhook, sharing, PDF, email and package workflows

### Integration endpoints

```text
POST /api/v1/integrations/{job_id}/access
GET  /api/v1/integrations/{job_id}/data
GET  /api/v1/integrations/{job_id}/json
GET  /api/v1/integrations/{job_id}/manifest
GET  /api/v1/integrations/{job_id}/openapi
POST /api/v1/integrations/{job_id}/webhook
```

The generated API key is used as:

```text
Authorization: Bearer gm_...
```

## Core principle

GraphMind must not rely only on image embeddings. Numerical questions should be answered from structured chart data whenever possible, while the original image and extracted regions remain available for traceability.

## API

- `GET /health`
- `POST /api/v1/jobs`
- `GET /api/v1/jobs/{job_id}`
- `GET /api/v1/jobs/{job_id}/results`
- Integration endpoints listed above

## Run locally

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Then open the GraphMind interface at the server root. FastAPI also exposes interactive API documentation at `/docs`.

## Project status

Early MVP with a functional delivery/integration layer. OCR and visual extraction remain pluggable components; full numeric chart extraction still requires a production-grade vision/model adapter.
