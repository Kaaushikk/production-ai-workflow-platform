import json
import random
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import cast

import numpy as np
import torch
from torch import nn

from inference_service.data import generate_operational_data
from inference_service.model import FEATURE_NAMES, AnomalyAutoencoder


@dataclass(frozen=True)
class ClassificationMetrics:
    precision: float
    recall: float
    f1: float
    false_positive_rate: float
    test_examples: int
    test_anomalies: int


def classification_metrics(labels: np.ndarray, predictions: np.ndarray) -> ClassificationMetrics:
    true_positive = int(np.sum((labels == 1) & (predictions == 1)))
    false_positive = int(np.sum((labels == 0) & (predictions == 1)))
    false_negative = int(np.sum((labels == 1) & (predictions == 0)))
    true_negative = int(np.sum((labels == 0) & (predictions == 0)))
    precision = (
        true_positive / (true_positive + false_positive)
        if true_positive + false_positive
        else 0
    )
    recall = (
        true_positive / (true_positive + false_negative)
        if true_positive + false_negative
        else 0
    )
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0
    false_positive_rate = (
        false_positive / (false_positive + true_negative)
        if false_positive + true_negative
        else 0
    )
    return ClassificationMetrics(
        precision=precision,
        recall=recall,
        f1=f1,
        false_positive_rate=false_positive_rate,
        test_examples=len(labels),
        test_anomalies=int(labels.sum()),
    )


def reconstruction_scores(
    model: AnomalyAutoencoder, features: np.ndarray, mean: np.ndarray, std: np.ndarray
) -> np.ndarray:
    tensor = torch.from_numpy(((features - mean) / std).astype(np.float32))
    with torch.inference_mode():
        reconstructed = model(tensor)
        return cast(np.ndarray, torch.mean((reconstructed - tensor) ** 2, dim=1).numpy())


def train_model(output_dir: Path, seed: int = 42, epochs: int = 80) -> dict[str, object]:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    train = generate_operational_data(seed, normal_count=2400, anomaly_count=0)
    validation = generate_operational_data(seed + 1, normal_count=600, anomaly_count=0)
    test = generate_operational_data(seed + 2, normal_count=900, anomaly_count=300)

    mean = train.features.mean(axis=0)
    std = train.features.std(axis=0)
    std[std == 0] = 1
    normalized_train = ((train.features - mean) / std).astype(np.float32)
    tensor = torch.from_numpy(normalized_train)
    model = AnomalyAutoencoder()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
    loss_function = nn.MSELoss()
    model.train()
    for _ in range(epochs):
        optimizer.zero_grad()
        loss = loss_function(model(tensor), tensor)
        loss.backward()
        optimizer.step()
    model.eval()

    validation_scores = reconstruction_scores(model, validation.features, mean, std)
    threshold = float(np.quantile(validation_scores, 0.99))
    test_scores = reconstruction_scores(model, test.features, mean, std)
    predictions = (test_scores > threshold).astype(np.int64)
    learned_metrics = classification_metrics(test.labels, predictions)

    z_scores = np.max(np.abs((test.features - mean) / std), axis=1)
    baseline_predictions = (z_scores > 3.0).astype(np.int64)
    baseline_metrics = classification_metrics(test.labels, baseline_predictions)

    version = "anomaly-autoencoder-v1"
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = output_dir / f"{version}.pt"
    report_path = output_dir / f"{version}-metrics.json"
    torch.save(
        {
            "version": version,
            "feature_names": list(FEATURE_NAMES),
            "state_dict": model.state_dict(),
            "mean": mean.tolist(),
            "std": std.tolist(),
            "threshold": threshold,
            "training_seed": seed,
            "epochs": epochs,
        },
        artifact_path,
    )
    report: dict[str, object] = {
        "model_version": version,
        "data": {
            "source": "deterministic synthetic operational metrics",
            "training_normal": len(train.features),
            "validation_normal": len(validation.features),
            "test_examples": len(test.features),
            "test_anomalies": int(test.labels.sum()),
            "seed": seed,
        },
        "threshold": threshold,
        "autoencoder": asdict(learned_metrics),
        "zscore_baseline": asdict(baseline_metrics),
    }
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> None:
    report = train_model(Path("artifacts"))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

