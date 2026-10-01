# Operations runbook

## API unavailable

Check the API deployment and `/health`, then `/ready`. A healthy process with failed readiness usually indicates PostgreSQL connectivity. Inspect trace-correlated logs, database connection limits, DNS, and the latest migration job before restarting anything.

## Outbox backlog increasing

Query pending `outbox_events` ordered by `next_attempt_at`. Check Kafka reachability and dispatcher errors. Delivery retries automatically with bounded backoff. Do not delete rows to clear the graph; restore Kafka, confirm the backlog drains, and verify processed-event growth.

## Consumer lag increasing

Check event-worker replicas, Kafka consumer-group state, database latency, and dead-letter traffic. Replaying a valid message is safe because processing records a unique event ID before committing the Kafka offset.

## Redis unavailable

The API logs the dependency error and continues without enforcing rate limits. Restore Redis, confirm `PING`, and verify rate-limit keys begin appearing. If strict abuse protection is required during the incident, enforce a temporary gateway limit.

## Elevated query latency

Use the Grafana p95 panel and Tempo traces to separate HTTP, SQL, retrieval, and application time. Check corpus size because the baseline retrieval implementation scores a tenant's candidates in the API process. Scale claims require the database-side retrieval improvement described in the architecture notes.

## Model readiness failure

Confirm the artifact exists, its manifest hash matches, and the container has enough memory. Roll back to the last verified image if the artifact or runtime changed. Never change the anomaly threshold without regenerating the versioned evaluation report.

## Deployment rollback

Roll deployments back to the prior immutable image digest. Database migrations in this project are additive; inspect the migration before considering a downgrade. Preserve outbox, processed-event, query, and audit records during recovery.
