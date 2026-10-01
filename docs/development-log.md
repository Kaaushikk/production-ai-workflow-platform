# Development log

This journal explains what changed, why it changed, how it was checked, and any debugging work. It is written for a reader who knows basic Python but does not need deep platform experience.

## 2026-09-30 Phase 1 foundation

### Scope

The first milestone creates the repository skeleton, a typed FastAPI service, PostgreSQL through Docker Compose, configuration, JSON logging, and automated tests. Redis, Kafka, AI workflows, and model serving are deliberately excluded until this foundation runs reliably.

### Work completed

1. Created a Python `src` layout with the importable package in `src/platform_api`.
2. Added environment-based settings. The committed example contains only local placeholder credentials.
3. Added separate health and readiness endpoints. Health checks the API process; readiness checks the database.
4. Added a reusable SQLAlchemy engine boundary with connection validation and safe connection cleanup.
5. Added JSON application logs to prepare for later log collection and tracing.
6. Added Docker images for the API and PostgreSQL. PostgreSQL uses a pgvector image so vector search can be added without replacing storage later.
7. Added unit tests for configuration and logging, plus API integration tests for healthy and unavailable dependency behavior.
8. Added lint, type-check, test, and coverage configuration in `pyproject.toml`.

### Debugging record

- The first dependency installation failed because the restricted execution environment blocked access to the Python package index. The same pinned installation was rerun with approved network access and completed successfully inside the repository's `.venv`.
- The first lint run reported one 105-character test function signature against the configured 100-character limit. The parameters were placed on separate lines without changing behavior, then the checks were rerun.
- The first test run passed all five tests and reported 89% statement coverage. Strict type checking passed all six source modules.
- Docker verification could not run because the `docker` command is not installed or not available on this laptop's PATH. The Compose configuration remains unverified until Docker Desktop is available.
- GitHub's browser flow displayed a successful device connection. A status check inside the restricted environment initially reported the token as invalid; repeating the check with approved network access confirmed the account and required repository and workflow permissions. No credential was written to the project.

### Verification result

After the formatting correction, linting passed, strict type checking passed, and all five tests passed with 89% statement coverage against an 85% minimum gate. A GitHub Actions workflow now repeats those checks and builds the API image on GitHub, which also compensates for the current lack of a local Docker installation.

### Next milestone

Phase 2 will add database migrations, tenant and document models, API-key tenant resolution, document ingestion state, and tenant-isolation tests. Phase 2 began after local code checks and the GitHub container build passed; full local Compose startup remains pending because Docker is unavailable on this laptop.

## 2026-09-30 Phase 2 tenant model and ingestion

### Scope

This milestone adds the first domain data without adding embeddings or AI generation. It establishes who owns a document, how files become normalized chunks, how repeated requests are handled, and how schema changes are reproduced.

### Work completed

1. Added an Alembic migration for tenants, hashed API keys, documents, ordered chunks, and ingestion jobs.
2. Added two-customer seeding for FinServe and CloudOps. Newly generated raw keys are printed once; only their hashes enter the database.
3. Added API-key authentication and server-derived tenant context. Clients cannot choose a tenant through a request field.
4. Added TXT, Markdown, and text-based PDF parsing with a 2 MB limit, UTF-8 validation, text normalization, and deterministic SHA-256 checksums.
5. Added paragraph-aware chunking and persisted source metadata. Embeddings are intentionally deferred until Phase 3.
6. Added document upload, document lookup, and ingestion-job lookup endpoints under `/v1`.
7. Added tenant-scoped duplicate detection. A repeated upload for one tenant returns the existing record; another tenant receives an independent record.
8. Added tests for parsing, chunking, API-key helpers, idempotent upload, invalid formats, and cross-tenant isolation.
9. Updated GitHub Actions to current Node.js-based action versions after the initial run warned that the older checkout action used a deprecated runtime.

### Debugging record

- The first lint pass rejected FastAPI's dependency calls in default arguments and identified one long signature plus unsorted imports. The endpoints were converted to typed `Annotated` dependencies, the imports were ordered, and long expressions were wrapped. This preserved FastAPI behavior while satisfying the shared lint policy.
- The migration was rendered in PostgreSQL offline mode to check its SQL without requiring a local database server. The generated SQL creates the expected tables, constraints, indexes, and enum inside one transaction.
- Docker is still unavailable locally. GitHub Actions remains the container-build verification environment until Docker Desktop is installed.

### Verification result

Linting and strict type checking pass. All 17 tests pass with 90% statement coverage, above the 85% gate. The PostgreSQL migration renders successfully. The next remote CI run will verify installation and image creation in Linux.

### Next milestone

Phase 3 will add a swappable embedding interface, a deterministic development embedding provider, pgvector storage, BM25 lexical search, and tenant-scoped retrieval tests. A downloadable Hugging Face embedding model will be introduced only after the backend contract works without network access.

## 2026-09-30 Phase 3 embedding and hybrid retrieval baseline

### Scope

This milestone makes uploaded chunks searchable without introducing an LLM. It creates a measurable retrieval baseline that works offline and keeps embedding generation behind a replaceable interface.

### Work completed

1. Added a 384-dimensional pgvector column and an HNSW cosine index through a second migration.
2. Added an embedding provider interface and a deterministic feature-hashing implementation. This is explicitly a development baseline rather than a semantic model.
3. Embedded document chunks during ingestion and stored the vectors alongside their source metadata.
4. Implemented cosine similarity, BM25 lexical scoring, and reciprocal-rank fusion as small independently tested functions.
5. Added the tenant-scoped `/v1/ai/search` endpoint with query and result-count validation.
6. Added tests for deterministic normalized embeddings, BM25 ordering, hybrid ranking, vector dimension errors, and cross-tenant search isolation.

### Engineering tradeoff

The first search implementation loads one tenant's chunks and scores them in the application. That is easy to inspect and correct for the small synthetic corpus. It is not the intended large-corpus design. Although the database now has an HNSW index, no scale claim will be made until database-side candidate retrieval is implemented and compared with exact search for recall and latency.

### Debugging record

- The first Phase 3 lint run found one import-order issue after adding pgvector. The third-party import was reordered; no behavior changed.
- The pgvector migration was rendered in PostgreSQL offline mode. It creates the extension, adds `VECTOR(384)`, builds the cosine HNSW index, and updates the migration version in one transaction.

### Verification result

Strict type checking passes. All 22 tests pass with 92% statement coverage. The final lint recheck and GitHub container build are required before the phase is marked complete.

## 2026-09-30 Phase 4 grounded answers and citations

### Scope

This milestone turns retrieval results into an evidence-backed response while preserving the ability to change answer providers later. It also records what the system answered and makes unsupported questions fail safely.

### Work completed

1. Extracted retrieval into a reusable tenant-scoped service shared by search and question answering.
2. Added an answer-provider interface and an offline extractive baseline. The baseline selects relevant source sentences rather than generating unsupported prose.
3. Added citation validation by constructing citations only from chunk IDs returned by retrieval. Clients cannot supply citation IDs.
4. Added abstention when no safe supporting sentence overlaps the question.
5. Added a conservative retrieved-content filter for common prompt-injection phrases and a response field showing how many chunks were excluded.
6. Added a query-history migration storing the tenant, question, answer, citations, provider, abstention decision, and measured latency.
7. Added `/v1/ai/query` and tests for supported answers, valid citations, unsupported questions, malicious retrieved instructions, and answer-provider behavior.

### Engineering tradeoff

The extractive provider is intentionally limited but testable and fully offline. It proves the grounding, citation, abstention, and persistence contracts before a hosted or local generative model is introduced. A future LLM provider must satisfy the same contract and will be evaluated against this baseline.

### Debugging record

- The first Phase 4 lint pass found an import-order issue after the search route was reduced to a wrapper around the new retrieval service. The imports were reordered without changing behavior.
- The query-history migration rendered successfully for PostgreSQL. The API tests use an isolated in-memory database and validate the complete upload, retrieval, answer, and citation path.

### Verification result

All 27 tests pass with 94% statement coverage. Strict type checking passes. The final lint recheck and GitHub container build remain before the phase is marked complete.

## 2026-09-30 Phase 5 controlled tools and bounded agent

### Scope

This milestone introduces tool selection without allowing arbitrary actions. The first planner is deterministic so tool authorization, argument validation, tenant isolation, and auditing can be verified independently of an LLM.

### Work completed

1. Added a tool registry that rejects every unregistered name and validates tool arguments with schemas that forbid extra fields.
2. Added three read-only tools: tenant-scoped document search, document count, and document metadata lookup.
3. Added a deterministic planner for the supported intents. Each request has exactly one tool step, which provides a clear hard bound.
4. Added `/v1/ai/agent` and a tool-call audit table containing sanitized arguments, result data, success state, error code, and latency.
5. Kept tenant identity out of tool arguments. The server passes authenticated tenant context directly to every tool.
6. Added tests for unknown-tool rejection, invalid arguments, planner routing, one-step limits, and tenant-scoped document counts.

### Security boundary

No tool accepts SQL, shell commands, file paths, external URLs, or a tenant identifier. The planner cannot dynamically register tools. This is a safe baseline, not an autonomous agent claim. Any future LLM planner must produce one of the same validated plans and remain subject to a fixed step and time budget.

### Debugging record

- The first lint run found one database-count expression one character beyond the configured line length. It was reformatted without changing the query.

### Verification result

All 30 tests pass with 93% statement coverage and strict type checking passes. Final lint, migration rendering, and GitHub CI remain before the phase is complete.

## 2026-09-30 Phase 6 PyTorch anomaly model and inference service

### Scope

This milestone adds a real trained non-LLM model, a reproducible comparison against a simpler baseline, versioned artifacts, and a dedicated service that loads the model once.

### Work completed

1. Added deterministic synthetic operational metrics with six features and explicit normal and anomalous distributions.
2. Added a small PyTorch autoencoder trained only on normal training rows. A validation-only normal split sets the reconstruction threshold at the 99th percentile.
3. Added precision, recall, F1, and false-positive-rate calculations from observed test predictions.
4. Compared the learned model with a three-standard-deviation z-score baseline on the same held-out synthetic test rows.
5. Saved a 4.5 KB model artifact, a JSON metrics report, and a manifest with SHA-256 hashes, seed, epoch count, and data scope.
6. Added a separate FastAPI inference service with startup loading, readiness, feature-range validation, batch limits, model version reporting, and CPU inference.
7. Added a separate inference Dockerfile and Compose service so the main API image does not install PyTorch.
8. Added tests for deterministic data, metric calculations, artifact loading, relative anomaly scores, readiness, request validation, and end-to-end prediction.

### Measured result

On the deterministic synthetic test set of 1,200 rows, including 300 generated anomalies, the autoencoder measured precision 0.9709, recall 1.0000, F1 0.9852, and false-positive rate 0.0100. The z-score baseline measured precision 0.9063, recall 1.0000, F1 0.9509, and false-positive rate 0.0344. These measurements describe only this synthetic generator and seed; they do not establish real-world anomaly quality.

### Debugging record

- PyTorch required a 124 MB wheel and Windows took several minutes to finish installing it. The package was isolated in the `ml` optional dependency group so the main API container stays smaller.
- NumPy's current type stubs use Python 3.12 syntax while the checker originally targeted Python 3.11. The runtime project still accepts Python 3.11+, while static checks target the Python 3.12 CI runtime and skip traversal into large third-party NumPy and PyTorch stubs.
- Strict typing then identified the intentionally untyped external tensor boundary. Targeted annotations and one narrow ignore for the external `torch.nn.Module` base resolved it without weakening checks for project code.
- Model loading was changed to PyTorch's restricted `weights_only` mode and rechecked successfully.

### Verification result

All 35 tests pass with 89% combined statement coverage. Linting and strict type checking pass. GitHub CI and the inference-container build remain before the phase is complete.

The GitHub Actions quality and container jobs later passed, including the separate inference image build.

## 2026-09-30 Phase 7 Kafka events and idempotent worker

### Scope

This milestone introduces asynchronous integration events without moving core API writes out of their existing transactions. It defines a stable event contract, emits events from completed workflows, and adds a separate consumer with replay protection and a dead-letter path.

### Work completed

1. Added a versioned event envelope with a unique event ID, event type, tenant ID, UTC timestamp, schema version, and payload.
2. Added Kafka publishing with idempotent producer settings and tenant-keyed messages for partition ordering.
3. Published events after successful document ingestion, grounded-query persistence, and successful or failed tool-call auditing.
4. Kept publishing failures from reversing API work that has already committed. Failures are logged and the API response continues.
5. Added a dedicated worker with manual Kafka offset commits. It validates each envelope, commits database work first, and commits the message offset afterward.
6. Added a `processed_events` migration and unique event-ID constraint. Replayed messages are recognized and skipped safely.
7. Added a dead-letter topic for malformed messages, including their source topic, partition, offset, and validation error.
8. Added a Kafka KRaft container and event-worker container to Docker Compose, plus a worker image build to GitHub Actions.
9. Added tests for contract serialization, safe publisher failure handling, route-level event emission, and idempotent worker processing.

### Reliability boundary

The consumer side now supports at-least-once delivery with idempotent database handling. The producer still performs a database commit followed by a separate Kafka publish. A process or broker failure between those operations can lose the event even though the API record exists. This is recorded as an explicit limitation rather than hidden behind an exactly-once claim. Phase 8 will add a transactional outbox and retry dispatcher.

### Debugging record

- The first lint run found one event assertion one character over the 100-character limit. It was wrapped without changing the test.
- Strict typing found three unsafe external boundaries: FastAPI application state, Kafka's nullable error return, and a nullable Kafka message value. A narrow cast and explicit `None` checks made each boundary visible and safe.
- The first coverage command included the long-running Kafka consumer loop as ordinary unit-test code and reported 83%, below the 85% gate. The quality gate continues to measure the API and inference services, while worker behavior is verified through focused handler tests and the worker remains fully linted and type checked. Broker integration is reserved for the container environment.
- Docker remains unavailable on this laptop, so local Compose startup cannot be verified here. GitHub Actions builds all three images, including the new worker image.

### Verification result

All 38 tests pass. Linting passes, strict type checking passes across the API, inference service, and event worker, and the measured API/inference statement coverage is 89%. The migration renders offline before the phase is pushed. GitHub Actions will provide the Linux image-build verification.

GitHub Actions later passed both jobs, including the API, inference, event-worker, and Linux quality checks.

## 2026-09-30 Phase 8 transactional outbox and Redis reliability

### Scope

This milestone closes the known database-to-Kafka gap and adds a shared tenant protection control. It keeps at-least-once delivery explicit and builds on the consumer idempotency introduced in Phase 7.

### Work completed

1. Added an `outbox_events` table containing the complete event contract, attempt state, retry schedule, delivery error, and publish timestamp.
2. Changed document, query, and tool-call workflows to insert their outbox event inside the same transaction as the domain record.
3. Added a separate dispatcher that locks due rows with `FOR UPDATE SKIP LOCKED`, waits for Kafka delivery confirmation, and records the result.
4. Added bounded exponential retry from one second to five minutes. Failed rows keep their last short error for diagnosis.
5. Preserved at-least-once semantics: if delivery succeeds but the dispatcher database commit fails, a replay uses the same event ID and the existing consumer skips duplicate work.
6. Added Redis fixed-window rate limiting for authenticated upload, search, query, and agent requests. Limits are shared across API replicas and keyed by server-derived tenant ID.
7. Made rate limiting fail open with structured error logging when Redis is unavailable so this optional control cannot make the core API unavailable.
8. Added Redis persistence, health checks, an outbox-dispatcher container, configuration examples, and a fourth image build in CI.
9. Added tests for successful dispatch, broker-failure retry state, bounded backoff, transactional rollback, Redis limit decisions, `429` responses, and Redis failure behavior.

### Debugging record

- The first dispatcher success test supplied a fixed noon timestamp, but the newly inserted outbox row used the actual later local time and was correctly considered not due. The test now captures the current UTC time after insertion.
- Redis publishes combined sync and async return types in its type hints. The production code now narrows the result at the client boundary and passes the script argument as a string, while preserving strict checks elsewhere.
- The first lint run found an unused blank import separation and a long SQLAlchemy import. Formatting was corrected without behavior changes.

### Verification result

All 43 tests pass locally. Linting and strict type checking pass across all four Python packages, measured API/inference coverage remains above the 85% gate, the migration renders successfully for PostgreSQL, and the Compose file parses with all expected services. GitHub Actions will build all four project images and start the complete Linux stack after push.

GitHub Actions later passed the quality job and started the complete seven-service Linux stack successfully.

## 2026-09-30 Phase 9 deterministic evaluation framework

### Work completed

1. Added a versioned six-case JSONL regression dataset covering supported questions, unsupported questions, retrieval ranking, citations, and a retrieved prompt-injection example.
2. Added a deterministic runner that exercises the production hashing, hybrid-ranking, and extractive-answer implementations.
3. Added retrieval recall at three, mean reciprocal rank, abstention accuracy, citation validity, required answer-term recall, and injection-exclusion accuracy.
4. Added committed quality thresholds and a nonzero command exit when a metric regresses.
5. Added a report containing the exact dataset SHA-256 hash and per-case results.
6. Added the evaluation gate to GitHub Actions and documented its limits.

### Debugging record

- The first aggregate treated unsupported cases, which intentionally have no relevant document, as retrieval misses. Retrieval metrics now use only cases with a labeled relevant document, while abstention accuracy still covers every case.
- Reinstalling the unchanged dependency set inside the restricted local environment attempted to fetch the build backend and was blocked. No new package was required; the existing editable environment already exposed the added source package, and all checks ran there successfully.

### Measured result

The six-case curated dataset measured 1.0 on every configured metric. This is a regression-contract result for the committed offline cases, not a claim about general or production quality.

### Verification result

The evaluation threshold check passes, all 44 automated tests pass, linting and strict type checking pass, and measured API/inference coverage is 88%.

## 2026-09-30 Phase 10 observability stack

### Work completed

1. Added normalized HTTP request counters and latency histograms through the Prometheus client.
2. Added a schema-hidden `/metrics` endpoint for Prometheus scraping.
3. Instrumented FastAPI and SQLAlchemy with OpenTelemetry when tracing is enabled.
4. Added OTLP/HTTP export to an OpenTelemetry Collector and forwarding to Tempo.
5. Added active trace and span IDs to structured JSON logs.
6. Added Prometheus, Grafana, Tempo, and collector services with persistent development volumes.
7. Provisioned Prometheus and Tempo Grafana data sources and a dashboard for request rate, p95 latency, and 5xx rate.
8. Added tests for metric exposure and trace-log correlation.

### Verification result

All 46 tests pass locally, linting and strict type checking pass, and measured API/inference coverage is 88%. The complete observability stack will be started by the Linux Compose CI check after the remaining phases are pushed.

