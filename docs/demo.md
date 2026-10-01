# Demo walkthrough

1. Start the stack with `docker compose up --build` and show that all services become healthy.
2. Open the API documentation at `http://localhost:8000/docs` and Grafana at `http://localhost:3000`.
3. Seed the two sample tenants and save one displayed development key.
4. Upload a policy stating that payment timeouts require retrying after five minutes.
5. Search for `payment timeout` and explain vector, BM25, and reciprocal-rank-fusion fields.
6. Ask how payment timeouts should be handled. Show the grounded sentence, citation, query record, and matching outbox event.
7. Ask an unsupported question and show the abstention response.
8. Run the bounded agent document-count task and show its audit record.
9. Call the inference service with normal and anomalous metric rows and compare scores without claiming real-world model accuracy.
10. Show that the dispatcher marks the outbox row published and the worker stores its event ID once.
11. Generate several requests, then show Grafana metrics, a Tempo trace, and the matching trace ID in JSON logs.
12. Run `python -m evaluation.runner --check` and explain the dataset scope and hash.

The demo should take about ten minutes. Use only generated sample data and local development credentials.
