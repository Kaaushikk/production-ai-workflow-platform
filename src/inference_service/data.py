from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class DatasetSplit:
    features: np.ndarray
    labels: np.ndarray


def generate_operational_data(seed: int, normal_count: int, anomaly_count: int) -> DatasetSplit:
    generator = np.random.default_rng(seed)
    normal = np.column_stack(
        [
            generator.normal(45, 10, normal_count),
            generator.normal(180, 35, normal_count),
            generator.beta(1.5, 45, normal_count),
            generator.normal(120, 20, normal_count),
            generator.normal(55, 8, normal_count),
            generator.poisson(3, normal_count),
        ]
    )
    anomaly = np.column_stack(
        [
            generator.normal(91, 5, anomaly_count),
            generator.normal(700, 120, anomaly_count),
            generator.beta(7, 10, anomaly_count),
            generator.normal(45, 15, anomaly_count),
            generator.normal(88, 5, anomaly_count),
            generator.poisson(24, anomaly_count),
        ]
    )
    features = np.vstack([normal, anomaly]).astype(np.float32)
    labels = np.concatenate(
        [np.zeros(normal_count, dtype=np.int64), np.ones(anomaly_count, dtype=np.int64)]
    )
    order = generator.permutation(len(features))
    return DatasetSplit(features[order], labels[order])
