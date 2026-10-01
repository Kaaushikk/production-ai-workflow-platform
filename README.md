# Production AI Workflow and ML Serving Platform

A portfolio project for building and evaluating a multi-tenant AI application with grounded retrieval, controlled tools, asynchronous processing, and a separately served ML model. The repository is being implemented in runnable phases; only verified features are described as complete.

## Current status

Phases 1 through 7 are implemented: the API and storage foundation, tenant-scoped AI workflows, bounded tools, a trained PyTorch anomaly model, and Kafka-based asynchronous event processing. See [the development log](docs/development-log.md) for the running implementation record.

## Repository tree

```text
.
|-- docs/
|   |-- architecture.md
|   `-- development-log.md
|-- src/platform_api/
|   |-- routes/documents.py
|   |-- routes/query.py
|   |-- routes/agent.py
|   |-- agent.py
|   |-- auth.py
|   |-- answers.py
|   |-- config.py
|   |-- database.py
|   |-- dependencies.py
|   |-- embeddings.py
|   |-- ingestion.py
|   |-- logging.py
|   |-- main.py
|   |-- models.py
|   |-- retrieval.py
|   |-- search_service.py
|   |-- tools.py
|   `-- schemas.py
|-- src/inference_service/
|   |-- data.py
|   |-- model.py
|   |-- training.py
|   `-- main.py
|-- src/event_worker/
|   |-- handler.py
|   `-- main.py
|-- artifacts/
|   |-- anomaly-autoencoder-v1.pt
|   |-- anomaly-autoencoder-v1-metrics.json
|   `-- manifest.json
|-- migrations/versions/0001_tenants_and_ingestion.py
|-- scripts/seed_tenants.py
|-- tests/
|   |-- integration/test_system_routes.py
|   `-- unit/
|       |-- test_config.py
|       `-- test_logging.py
|-- .github/workflows/ci.yml
|-- .env.example
|-- .gitignore
|-- Dockerfile
|-- Dockerfile.worker
|-- docker-compose.yml
`-- pyproject.toml
```

## Run with Docker

Requirements: Docker Desktop with Docker Compose.

```powershell
Copy-Item .env.example .env
docker compose up --build
```

Open `http://localhost:8000/docs` for the generated API documentation. Check:

```powershell
Invoke-RestMethod http://localhost:8000/health
Invoke-RestMethod http://localhost:8000/ready
```

Expected results are `status: ok` for health and `status: ready` with `database: ok` for readiness.

The inference service runs on port 8001. Its readiness endpoint reports the loaded model version:

```powershell
Invoke-RestMethod http://localhost:8001/ready
```

Create the two simulated tenants and development API keys:

```powershell
docker compose exec api python scripts/seed_tenants.py
```

The script prints each raw key once. Save the keys locally; the database stores only SHA-256 hashes. Submit a UTF-8 TXT or Markdown file up to 2 MB:

```powershell
curl.exe -X POST http://localhost:8000/v1/documents `
  -H "X-API-Key: YOUR_KEY" `
  -F "title=Example policy" `
  -F "file=@.\example.md;type=text/markdown"
```

Stop the services with `docker compose down`. Add `-v` only when you intentionally want to delete the local PostgreSQL volume.

## Run tests locally

Python 3.11 or newer is required.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev,ml]"
ruff check .
mypy src
pytest --cov=platform_api --cov=inference_service --cov-report=term-missing
```

The readiness success path needs PostgreSQL. Automated tests use controlled dependencies and an isolated database; container startup verifies the real service connections.

## Phase 2 behavior

- API keys are generated with a `pai_` prefix, displayed once, and stored only as hashes.
- Every document, chunk, and ingestion job carries a tenant ID. Lookups always filter by the authenticated tenant.
- TXT, Markdown, and text-based PDF files are accepted. Empty, oversized, unsupported, or unreadable uploads return a validation error.
- A SHA-256 checksum makes retries idempotent within a tenant. The same content can still be ingested independently by another tenant.
- Ingestion is synchronous for now so the persistence contract can be tested before Kafka workers are introduced.

## Phase 3 search

`POST /v1/ai/search` accepts a query and result limit. New chunks receive 384-dimensional vectors stored in pgvector. The current offline provider uses stable feature hashing, which makes tests and local development reproducible but does not provide the semantic quality of a trained embedding model. Results combine cosine similarity and BM25 scores with reciprocal-rank fusion.

The current search implementation scores the authenticated tenant's corpus in the application. This is deliberate for a small, inspectable baseline. The schema includes a pgvector HNSW index; a later performance milestone will move vector candidate selection into PostgreSQL and compare exact and approximate recall before claiming scalability.

## Phase 4 grounded query

`POST /v1/ai/query` retrieves tenant-scoped evidence and returns an answer whose numbered citations map only to the retrieved chunks. The current provider is an offline extractive baseline: it selects relevant source sentences and does not invent connecting prose. It abstains when no source sentence shares meaningful terms with the question.

Retrieved chunks containing common instruction-manipulation phrases are excluded before answering. This is one defense layer and is not presented as complete prompt-injection protection. Every query result, citation list, provider name, abstention decision, and measured request latency is stored in tenant-scoped query history.

## Phase 5 controlled tools

`POST /v1/ai/agent` uses a deterministic planner and exactly one read-only tool per request. The registry currently allows document search, tenant document count, and tenant-scoped document metadata lookup. Every argument is validated with a schema, the authenticated tenant is supplied by the server, and every successful or failed tool call is audited.

This baseline does not execute generated SQL, shell commands, arbitrary URLs, or client-supplied tenant IDs. It also does not claim autonomous reasoning. Later customer-specific tools will keep the same registry and audit contract.

## Phase 6 anomaly model

The ML component is a small PyTorch autoencoder trained only on normal synthetic operational metrics. It uses CPU, memory, latency, error rate, request rate, and queue depth. Training is deterministic and compares the learned reconstruction-error detector with a z-score baseline.

```powershell
.\.venv\Scripts\python.exe -m inference_service.training
```

The committed report is tied to model version `anomaly-autoencoder-v1`, seed 42, 2,400 normal training rows, 600 normal validation rows, and a 1,200-row synthetic test set containing 300 anomalies. On that synthetic test set, the autoencoder measured F1 `0.9852` and false-positive rate `0.0100`; the z-score baseline measured F1 `0.9509` and false-positive rate `0.0344`. These are reproducible synthetic-data results and are not claims about real production performance.

The separate inference service loads the artifact once at startup, validates batches of up to 100 rows, and returns anomaly scores, threshold decisions, and the exact model version. The artifact manifest records SHA-256 hashes for provenance.

## Phase 7 asynchronous events

Successful document ingestion, grounded queries, and tool calls publish versioned events to the `platform.events` Kafka topic. Every envelope contains a unique event ID, tenant ID, UTC timestamp, schema version, event type, and typed-by-convention payload. The API uses the tenant ID as the Kafka key so events for one tenant retain partition order.

The separate event worker disables automatic offset commits. It stores each handled event ID in PostgreSQL, then commits the Kafka offset. Redelivery is therefore safe for the implemented database-side handler: an event already recorded in `processed_events` is skipped. Invalid envelopes go to `platform.events.dlq` with source coordinates and validation details.

The API database commit and Kafka publish are currently separate operations. A broker failure after a successful API commit can leave that operation without an event. The next reliability phase will add a transactional outbox so committed work can be retried until published. No end-to-end delivery guarantee is claimed before that change.

## Configuration

All settings use the `APP_` prefix. Copy `.env.example` for local development and never commit real credentials. Docker Compose supplies its own database hostname because containers reach PostgreSQL by service name, while the default application setting uses `localhost` for a directly run API.

## Troubleshooting

- If port 8000 or 5432 is already in use, stop the conflicting process or change the host-side port in `docker-compose.yml`.
- If `/health` works but `/ready` returns `503`, inspect `docker compose ps` and `docker compose logs postgres` before changing application code.
- If Python cannot import `platform_api`, install the project in editable mode with `python -m pip install -e ".[dev]"`.
- If PowerShell blocks virtual-environment activation, call `.venv\Scripts\python.exe` directly for install and test commands.

## Roadmap

1. Foundation and PostgreSQL
2. Tenant model and ingestion — complete
3. Embeddings, pgvector, and BM25 — complete baseline
4. Hybrid RAG with citations — complete baseline
5. Safe tools and bounded agent behavior — complete baseline
6. PyTorch model training and inference service — complete
7. Kafka worker — complete baseline
8. Transactional outbox and Redis reliability features — next
9. Evaluation framework
10. OpenTelemetry, Prometheus, and Grafana
11. CI and load testing
12. Cloud deployment

Performance numbers and resume claims will be added only after reproducible measurement.
