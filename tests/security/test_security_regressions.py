from fastapi.testclient import TestClient

from platform_api.main import app


def test_responses_include_browser_hardening_headers() -> None:
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["cache-control"] == "no-store"


def test_metrics_do_not_expose_environment_secrets(monkeypatch: object) -> None:
    monkeypatch.setenv("APP_DATABASE_URL", "postgresql+psycopg://secret:value@db/platform")  # type: ignore[attr-defined]
    with TestClient(app) as client:
        response = client.get("/metrics")

    assert "secret:value" not in response.text
