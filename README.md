# Production AI Workflow and ML Serving Platform

A portfolio project for building and evaluating a multi-tenant AI application with grounded retrieval, controlled tools, asynchronous processing, and a separately served ML model. The repository is being implemented in runnable phases; only verified features are described as complete.

## Current status

Phases 1 through 5 are implemented: the API and storage foundation, tenant-scoped ingestion, hybrid retrieval, grounded answers, and bounded allow-listed tools with audit records. See [the development log](docs/development-log.md) for the running implementation record.

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
python -m pip install -e ".[dev]"
ruff check .
mypy src
pytest --cov=platform_api --cov-report=term-missing
```

The readiness success path needs PostgreSQL. Phase 1's automated test uses a controlled dependency failure to verify the `503` response without requiring a database in the unit-test process. Container startup verifies the real database connection.

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
6. PyTorch model training and inference service — next
7. Kafka worker
8. Redis reliability features
9. Evaluation framework
10. OpenTelemetry, Prometheus, and Grafana
11. CI and load testing
12. Cloud deployment

Performance numbers and resume claims will be added only after reproducible measurement.
