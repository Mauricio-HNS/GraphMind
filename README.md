# GraphMind

GraphMind is a chart intelligence engine that transforms batches of charts into structured, AI-ready knowledge.

<p align="center">
  <a href="https://mauricio-hns.github.io/GraphMind/"><strong>TRY GRAPHMIND</strong></a> ·
  <a href="https://mauricio-hns.github.io/GraphMind/">Web Interface</a> ·
  <a href="https://github.com/Mauricio-HNS/GraphMind">Source Code</a>
</p>

## Vision

Upload one chart or hundreds of charts, describe what you want to discover, and let GraphMind prepare visual information for downstream AI analysis.

## GitHub-native mode

GraphMind can run directly inside GitHub Actions. A repository becomes the analysis workspace: put charts in a folder, write the question in a Markdown prompt, and GraphMind generates versioned Markdown, JSON and CSV results.

```text
charts/
  sales-2024.png
  sales-2025.png

prompts/
  analysis.md

results/
  analysis.md
  analysis.json
  extracted-data.csv
```

The repository can use the GraphMind Action with:

```yaml
name: GraphMind Analysis

on:
  workflow_dispatch:
  push:
    paths:
      - "charts/**"
      - "prompts/**"

jobs:
  analyze:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: Mauricio-HNS/GraphMind@main
        with:
          input: charts
          prompt-file: prompts/analysis.md
          output: results
```

For production use, pin the Action to a release tag or commit SHA rather than `main`.

The included example workflow at `.github/workflows/example-graphmind.yml` can be copied into another repository and adapted to its chart directory.

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

Private-beta/early MVP. The GitHub-native workflow is now available for repository-based chart analysis. OCR and visual extraction remain pluggable components; full numeric chart extraction still requires a production-grade vision/model adapter. Low-confidence results must remain explicitly marked for review rather than being presented as verified facts.
