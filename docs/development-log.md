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

