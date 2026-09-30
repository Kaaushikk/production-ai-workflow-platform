from pathlib import Path

from fastapi.testclient import TestClient

from inference_service.main import create_app


def test_inference_service_loads_model_once_and_predicts() -> None:
    app = create_app(Path("artifacts/anomaly-autoencoder-v1.pt"))
    with TestClient(app) as client:
        ready = client.get("/ready")
        response = client.post(
            "/v1/predict",
            json={
                "rows": [
                    {
                        "cpu_percent": 99,
                        "latency_ms": 950,
                        "error_rate": 0.8,
                        "request_rate": 5,
                        "memory_percent": 98,
                        "queue_depth": 60,
                    }
                ]
            },
        )

    assert ready.status_code == 200
    assert ready.json()["model_version"] == "anomaly-autoencoder-v1"
    assert response.status_code == 200
    assert response.json()["predictions"][0]["is_anomaly"] is True


def test_inference_service_validates_feature_ranges() -> None:
    app = create_app(Path("artifacts/anomaly-autoencoder-v1.pt"))
    with TestClient(app) as client:
        response = client.post(
            "/v1/predict",
            json={
                "rows": [
                    {
                        "cpu_percent": 150,
                        "latency_ms": 1,
                        "error_rate": 0,
                        "request_rate": 1,
                        "memory_percent": 1,
                        "queue_depth": 0,
                    }
                ]
            },
        )

    assert response.status_code == 422

