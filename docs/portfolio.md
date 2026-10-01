# Portfolio and interview notes

Use these statements only for the implemented repository and keep the stated scope.

## Resume-ready bullets

- Built a multi-tenant AI workflow platform with FastAPI, PostgreSQL/pgvector, hybrid BM25-vector retrieval, grounded citations, abstention behavior, allowlisted tools, and tenant-isolated audit records.
- Implemented reliable asynchronous processing with Kafka, a transactional PostgreSQL outbox, broker-confirmed retries, dead-letter handling, and idempotent consumer receipts; added Redis tenant rate limiting.
- Trained and served a versioned PyTorch anomaly autoencoder and compared it with a z-score baseline on a reproducible synthetic dataset; the autoencoder measured 0.9852 F1 and 0.0100 false-positive rate on that specific generated test set.
- Added OpenTelemetry traces, trace-correlated JSON logs, Prometheus metrics, Tempo, provisioned Grafana dashboards, container CI, deterministic AI regression gates, and Kubernetes release manifests.
- Verified the documented 10-user, 60-second synthetic CI workload with 918 requests, zero failures, 17 ms p95, and 28 ms p99 on a one-document corpus; keep the runner and workload scope attached to these numbers.

## Interview talking points

- Explain why the database change and outbox insert share one transaction, and why delivery is still at least once.
- Explain why the consumer commits its Kafka offset only after its database transaction and how the event ID handles replay.
- Contrast the offline feature-hashing and extractive baselines with a production embedding or generative provider.
- Describe tenant identity as server-derived context rather than a tool or request argument.
- State that the perfect regression metrics describe six curated cases and that the anomaly metrics describe synthetic data only.
- Discuss the current application-side retrieval scaling limit and how to benchmark pgvector candidate retrieval before changing it.
- Walk through an incident using Prometheus, Tempo, and trace-correlated logs.

## Claims to avoid

Do not call the system production proven, exactly once, hallucination free, penetration tested, or accurate on real operational anomalies. No sustained load result should be quoted until the workload, hardware, dataset size, duration, and output are recorded together.
