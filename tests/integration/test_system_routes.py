from collections.abc import Iterator
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from platform_api.main import app


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


def test_health_reports_service_without_database(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["environment"] == "development"


def test_metrics_expose_request_count_and_latency(client: TestClient) -> None:
    client.get("/health")

    response = client.get("/metrics")

    assert response.status_code == 200
    assert "platform_http_requests_total" in response.text
    assert "platform_http_request_duration_seconds_bucket" in response.text


def test_readiness_reports_database_failure(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    failure = OperationalError("SELECT 1", {}, Exception("offline"))
    monkeypatch.setattr("platform_api.main.check_database", Mock(side_effect=failure))

    response = client.get("/ready")

    assert response.status_code == 503
    assert response.json() == {"detail": "Database unavailable"}

