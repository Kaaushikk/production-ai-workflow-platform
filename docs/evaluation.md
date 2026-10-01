# Evaluation guide

The regression evaluation is intentionally deterministic and offline. It checks whether changes to retrieval or answer construction break known behaviors before those changes reach a deployed environment.

## What is measured

- Retrieval recall at three checks whether each labeled relevant document appears in the first three results.
- Mean reciprocal rank rewards placing the first relevant document earlier.
- Abstention accuracy checks supported and unsupported questions.
- Citation validity requires every cited chunk ID to come from retrieved evidence.
- Answer-term recall checks case-specific required facts.
- Injection-exclusion accuracy checks whether retrieved text containing the configured attack phrases is excluded.

Run `python -m evaluation.runner --check`. The command writes `artifacts/evaluation-report-v1.json` and exits unsuccessfully if a metric falls below `evals/thresholds.json`. GitHub Actions runs the same command.

## Scope and limitations

Version 1 has six hand-authored cases for the offline hashing and extractive baselines. A perfect result means the implementation satisfies these six contracts. It is not an estimate of broad question-answering accuracy, production latency, or user satisfaction. New failure examples should be added before fixing the behavior so the dataset grows with observed defects.
