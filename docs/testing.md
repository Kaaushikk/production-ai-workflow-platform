# Testing and performance guide

The default quality workflow runs linting, strict typing, unit and integration tests, the AI regression evaluation, container builds, full-stack startup, and an API-to-Kafka smoke test. The smoke test creates a disposable tenant, uploads a document, sends concurrent grounded queries, and waits until every outbox event is both published and recorded by the idempotent consumer.

## Local checks

```powershell
ruff check .
mypy src
pytest --cov=platform_api --cov=inference_service --cov-report=term-missing
python -m evaluation.runner --check
```

Security regression tests live under `tests/security`. They run with the normal suite and currently cover response hardening, secret-free metrics, tenant isolation, API-key validation, injection filtering, tool allowlisting, input validation, and idempotent event recovery across the wider test set.

## Load test

Install the load-test dependency with `python -m pip install -e ".[load]"`, start and seed the stack, set `LOAD_TEST_API_KEY`, then run:

```powershell
locust -f load/locustfile.py --headless --users 10 --spawn-rate 2 `
  --run-time 60s --host http://localhost:8000 --only-summary
```

The GitHub `Performance` workflow exposes the user count and duration as manual inputs. Results depend on runner hardware, dataset size, service configuration, and network conditions. Record those conditions with any published result; this repository does not claim an unmeasured throughput or latency target.

## Recovery behavior

- Kafka delivery failure leaves the outbox row pending with a bounded retry time.
- A later successful attempt uses the same event ID.
- Consumer redelivery is skipped through the unique processed-event receipt.
- Invalid event envelopes move to the dead-letter topic.
- Redis failure is logged and rate limiting fails open by design.
