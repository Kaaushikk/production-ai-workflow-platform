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

Phase 2 will add database migrations, tenant and document models, API-key tenant resolution, document ingestion state, and tenant-isolation tests. Phase 2 begins only after the Phase 1 quality checks and local service startup pass.

