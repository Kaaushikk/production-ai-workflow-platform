# Production AI Workflow and ML Serving Platform

A portfolio project for building and evaluating a multi-tenant AI application with grounded retrieval, controlled tools, asynchronous processing, and a separately served ML model. The repository is being implemented in runnable phases; only verified features are described as complete.

## Current status

Phase 1 foundation is implemented: FastAPI, PostgreSQL, Docker Compose, configuration, structured logs, and system endpoint tests. See [the development log](docs/development-log.md) for the running implementation record.

## Repository tree

```text
.
|-- docs/
|   |-- architecture.md
|   `-- development-log.md
|-- src/platform_api/
|   |-- config.py
|   |-- database.py
|   |-- logging.py
|   |-- main.py
|   `-- schemas.py
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

## Configuration

All settings use the `APP_` prefix. Copy `.env.example` for local development and never commit real credentials. Docker Compose supplies its own database hostname because containers reach PostgreSQL by service name, while the default application setting uses `localhost` for a directly run API.

## Troubleshooting

- If port 8000 or 5432 is already in use, stop the conflicting process or change the host-side port in `docker-compose.yml`.
- If `/health` works but `/ready` returns `503`, inspect `docker compose ps` and `docker compose logs postgres` before changing application code.
- If Python cannot import `platform_api`, install the project in editable mode with `python -m pip install -e ".[dev]"`.
- If PowerShell blocks virtual-environment activation, call `.venv\Scripts\python.exe` directly for install and test commands.

## Roadmap

1. Foundation and PostgreSQL
2. Tenant model and ingestion
3. Embeddings, pgvector, and BM25
4. Hybrid RAG with citations
5. Safe tools and bounded agent behavior
6. PyTorch model training and inference service
7. Kafka worker
8. Redis reliability features
9. Evaluation framework
10. OpenTelemetry, Prometheus, and Grafana
11. CI and load testing
12. Cloud deployment

Performance numbers and resume claims will be added only after reproducible measurement.
