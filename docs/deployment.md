# Cloud deployment guide

The `deploy/kubernetes` base runs the four project images while using managed PostgreSQL with pgvector, Kafka, Redis, and OTLP services. This keeps stateful infrastructure under cloud-provider backups, encryption, and maintenance instead of placing portfolio-grade database manifests in the application repository.

## Prerequisites

1. A Kubernetes cluster with a metrics server and an ingress or gateway controller.
2. Managed PostgreSQL 16 with the `vector` extension enabled.
3. Managed Kafka and Redis endpoints reachable from the cluster.
4. An OTLP endpoint for the chosen observability backend.
5. Four images published by the `Release containers` GitHub workflow.

## Release and deploy

1. Run every CI check on the exact commit.
2. Create a version tag such as `v0.1.0`. The release workflow publishes API, inference, event-worker, and outbox-dispatcher images to GitHub Container Registry.
3. Copy `secret.example.yaml` outside the repository, replace every placeholder, and create `platform-secrets` through the cloud secret manager or an encrypted-secrets controller. Never commit the populated file.
4. Update the image tags in the manifests to the immutable release tag or digest.
5. Apply the namespace and configuration, create the secret, then apply the migration job. Wait for it to complete before rolling out the services.
6. Apply the remaining Kustomize resources and configure the external HTTPS gateway to route to the `api` service.
7. Verify `/health`, `/ready`, `/metrics`, one authenticated upload and query, outbox drain, consumer progress, inference readiness, traces, and dashboards.

```bash
kubectl apply -f deploy/kubernetes/namespace.yaml
kubectl apply -f deploy/kubernetes/configmap.yaml
kubectl apply -f /secure/path/platform-secrets.yaml
kubectl apply -f deploy/kubernetes/migration-job.yaml
kubectl wait --for=condition=complete job/database-migration -n ai-platform --timeout=180s
kubectl apply -k deploy/kubernetes
kubectl rollout status deployment/api -n ai-platform
```

The example is provider neutral. A live deployment requires a selected provider, region, DNS name, TLS certificate, service sizes, secret-manager integration, network rules, and billing approval.
