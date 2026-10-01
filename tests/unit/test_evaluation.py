from evaluation.runner import DEFAULT_DATASET, DEFAULT_THRESHOLDS, evaluate, threshold_failures


def test_regression_dataset_meets_committed_quality_thresholds() -> None:
    result = evaluate(DEFAULT_DATASET)

    assert result.case_count == 6
    assert len(result.dataset_sha256) == 64
    assert threshold_failures(result, DEFAULT_THRESHOLDS) == []
