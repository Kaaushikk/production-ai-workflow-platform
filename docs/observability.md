# Observability guide

Docker Compose starts an OpenTelemetry Collector, Tempo, Prometheus, and Grafana alongside the application services.

- The API emits FastAPI and SQLAlchemy spans over OTLP/HTTP.
- The collector validates and forwards traces to Tempo.
- JSON logs include active trace and span IDs for correlation.
- Prometheus scrapes normalized route counters and latency histograms from `/metrics`.
- Grafana provisions Prometheus and Tempo data sources plus the platform overview dashboard.

After `docker compose up --build`, open Grafana at `http://localhost:3000` and sign in with the local-only `admin` / `admin` credentials from Compose. Prometheus is available at `http://localhost:9090`, Tempo at `http://localhost:3200`, and raw API metrics at `http://localhost:8000/metrics`.

The supplied dashboard shows request rate, p95 latency, and 5xx rate. These panels become useful after generating traffic. Local credentials and storage are development defaults; a real deployment must source Grafana credentials from a secret manager and use durable managed storage.
