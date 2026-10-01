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

## Phase 7 event flow

```text
API request
  |-- commit domain record to PostgreSQL
  `-- publish versioned envelope to platform.events
                |
                v
            Kafka (KRaft)
                |
                v
       event worker, manual offset commit
          |-- validate envelope
          |-- insert unique processed_events receipt
          |-- commit database transaction
          `-- commit Kafka offset

Invalid envelope -> platform.events.dlq
```

Kafka provides at-least-once delivery to the consumer. The worker uses the event ID as an idempotency key and commits its offset only after the database transaction succeeds. Tenant ID is the message key so a tenant's events preserve ordering within a partition.

The producer is deliberately best-effort in this milestone: API work that has already committed does not become a failed client request if Kafka is unavailable. This creates a known dual-write gap between PostgreSQL and Kafka. A transactional outbox in the next reliability phase will close that gap by recording domain work and an unpublished event in one database transaction.

