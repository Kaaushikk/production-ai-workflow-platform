# Phase 1 architecture

The first phase establishes the smallest dependable platform boundary: an HTTP API and a PostgreSQL database. Later phases will add domain models, background processing, retrieval, model serving, and observability without putting those responsibilities inside route functions.

```text
Client
  |
  v
FastAPI API
  |-- /health  process health
  |-- /ready   dependency health
  |
  v
SQLAlchemy connection boundary
  |
  v
PostgreSQL with pgvector image
```

## Decisions

- `src` layout prevents imports from accidentally succeeding only because the repository root is on the Python path.
- `create_app` isolates application assembly and makes future dependency overrides testable.
- `/health` does not contact dependencies. It answers whether the API process is alive.
- `/ready` verifies PostgreSQL and returns `503` if the service cannot safely accept dependent work.
- SQLAlchemy owns connection pooling while PostgreSQL-specific access remains possible in later phases.
- The pgvector PostgreSQL image is used now so Phase 3 can add vector columns without replacing the database.
- Configuration comes from environment variables and `.env` stays untracked.
- JSON logs are enabled from the beginning so future fields can be consumed by telemetry systems.

## Planned boundaries

The API will remain thin. Domain services will implement ingestion, retrieval, agent tools, and evaluation. Repositories will own database queries. Provider interfaces will keep embedding and language-model vendors replaceable. A dedicated inference service and Kafka worker will be added only after the core request and storage paths work.

## Phase 2 data and request flow

```text
Upload request
  |-- X-API-Key -> SHA-256 lookup -> tenant context
  |-- validate filename, size, encoding, and readable text
  |-- checksum lookup within tenant
  |-- normalize and split text into ordered chunks
  `-- one transaction -> document + chunks + completed ingestion job
```

The raw API key is never persisted. Every read path combines the requested identifier with the authenticated tenant ID, so a valid identifier from another tenant behaves as unavailable. A database uniqueness constraint on tenant and checksum provides the final concurrency guard for duplicate uploads.

Ingestion remains synchronous in Phase 2. This keeps failure and transaction behavior observable while the schema is new. When Kafka is introduced, the same ingestion job will become the durable state record and the worker will make state transitions outside the request.

