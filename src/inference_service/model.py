from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import torch
from torch import nn

FEATURE_NAMES = (
    "cpu_percent",
    "latency_ms",
    "error_rate",
    "request_rate",
    "memory_percent",
    "queue_depth",
)


class AnomalyAutoencoder(nn.Module):  # type: ignore[misc]
    def __init__(self, feature_count: int = len(FEATURE_NAMES)) -> None:
        super().__init__()
        self.network = nn.Sequential(
            nn.Linear(feature_count, 4),
            nn.ReLU(),
            nn.Linear(4, 2),
            nn.ReLU(),
            nn.Linear(2, 4),
            nn.ReLU(),
            nn.Linear(4, feature_count),
        )

    def forward(self, features: torch.Tensor) -> torch.Tensor:
        return self.network(features)


@dataclass(frozen=True)
class Prediction:
    is_anomaly: bool
    score: float
    threshold: float


class LoadedModel:
    def __init__(self, artifact: Mapping[str, Any]) -> None:
        feature_names = tuple(artifact["feature_names"])
        if feature_names != FEATURE_NAMES:
            raise ValueError("Artifact feature order does not match the service contract")
        self.version = str(artifact["version"])
        self.threshold = float(artifact["threshold"])
        self.mean = np.asarray(artifact["mean"], dtype=np.float32)
        self.std = np.asarray(artifact["std"], dtype=np.float32)
        self.model = AnomalyAutoencoder()
        self.model.load_state_dict(artifact["state_dict"])
        self.model.eval()

    @classmethod
    def from_path(cls, path: Path) -> "LoadedModel":
        artifact = torch.load(path, map_location="cpu", weights_only=True)
        if not isinstance(artifact, Mapping):
            raise ValueError("Model artifact must contain a mapping")
        return cls(artifact)

    def predict(self, rows: list[list[float]]) -> list[Prediction]:
        values: Any = np.asarray(rows, dtype=np.float32)
        normalized = (values - self.mean) / self.std
        tensor = torch.from_numpy(normalized)
        with torch.inference_mode():
            reconstructed = self.model(tensor)
            scores = torch.mean((reconstructed - tensor) ** 2, dim=1).numpy()
        return [
            Prediction(bool(score > self.threshold), float(score), self.threshold)
            for score in scores
        ]

