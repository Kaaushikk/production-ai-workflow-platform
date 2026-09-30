from pathlib import Path

import numpy as np

from inference_service.data import generate_operational_data
from inference_service.model import LoadedModel
from inference_service.training import classification_metrics

ARTIFACT = Path("artifacts/anomaly-autoencoder-v1.pt")


def test_synthetic_data_is_deterministic_and_has_expected_labels() -> None:
    first = generate_operational_data(7, normal_count=10, anomaly_count=4)
    second = generate_operational_data(7, normal_count=10, anomaly_count=4)

    assert np.array_equal(first.features, second.features)
    assert np.array_equal(first.labels, second.labels)
    assert int(first.labels.sum()) == 4


def test_classification_metrics_use_observed_counts() -> None:
    metrics = classification_metrics(
        np.asarray([0, 0, 1, 1]), np.asarray([0, 1, 1, 0])
    )

    assert metrics.precision == 0.5
    assert metrics.recall == 0.5
    assert metrics.f1 == 0.5
    assert metrics.false_positive_rate == 0.5


def test_versioned_model_scores_obvious_anomaly_above_normal_row() -> None:
    model = LoadedModel.from_path(ARTIFACT)

    normal, anomaly = model.predict(
        [
            [45, 180, 0.02, 120, 55, 3],
            [99, 950, 0.8, 5, 98, 60],
        ]
    )

    assert model.version == "anomaly-autoencoder-v1"
    assert anomaly.score > normal.score
    assert anomaly.is_anomaly is True

