import argparse
import hashlib
import json
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from platform_api.answers import default_answer_provider
from platform_api.embeddings import default_embedding_provider
from platform_api.retrieval import Candidate, hybrid_rank
from platform_api.search_service import RetrievedChunk

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATASET = ROOT / "evals" / "datasets" / "rag-regression-v1.jsonl"
DEFAULT_THRESHOLDS = ROOT / "evals" / "thresholds.json"
DEFAULT_REPORT = ROOT / "artifacts" / "evaluation-report-v1.json"


@dataclass(frozen=True)
class EvaluationResult:
    dataset_sha256: str
    case_count: int
    metrics: dict[str, float]
    cases: list[dict[str, Any]]

    def as_dict(self) -> dict[str, Any]:
        return {
            "evaluation_version": "rag-regression-v1",
            "dataset_sha256": self.dataset_sha256,
            "case_count": self.case_count,
            "metrics": self.metrics,
            "cases": self.cases,
        }


def load_cases(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def evaluate_case(case: dict[str, Any]) -> dict[str, Any]:
    documents = case["documents"]
    texts = [str(document["text"]) for document in documents]
    candidates = [
        Candidate(
            key=str(index),
            text=text,
            embedding=default_embedding_provider.embed([text])[0],
        )
        for index, text in enumerate(texts)
    ]
    ranked = hybrid_rank(
        str(case["question"]),
        default_embedding_provider.embed([str(case["question"])])[0],
        candidates,
        limit=min(3, len(candidates)),
    )
    relevant = {str(index) for index, document in enumerate(documents) if document["relevant"]}
    ranked_keys = [item.candidate.key for item in ranked]
    relevant_ranks = [ranked_keys.index(key) + 1 for key in relevant if key in ranked_keys]
    recall = len(relevant.intersection(ranked_keys)) / max(1, len(relevant))
    reciprocal_rank = 1 / min(relevant_ranks) if relevant_ranks else 0.0

    retrieved = [
        RetrievedChunk(
            chunk_id=uuid.uuid5(uuid.NAMESPACE_URL, f"{case['id']}:chunk:{item.candidate.key}"),
            document_id=uuid.uuid5(
                uuid.NAMESPACE_URL, f"{case['id']}:document:{item.candidate.key}"
            ),
            title=f"{case['id']}-{item.candidate.key}.txt",
            text=item.candidate.text,
            vector_score=item.vector_score,
            lexical_score=item.lexical_score,
            hybrid_score=item.hybrid_score,
        )
        for item in ranked
    ]
    answer = default_answer_provider.answer(str(case["question"]), retrieved)
    retrieved_ids = {str(item.chunk_id) for item in retrieved}
    required_terms = [str(term).lower() for term in case["required_terms"]]
    term_recall = (
        sum(term in answer.text.lower() for term in required_terms) / len(required_terms)
        if required_terms
        else 1.0
    )
    unsafe_retrieved = sum(
        bool(documents[int(key)].get("unsafe", False)) for key in ranked_keys
    )
    return {
        "id": case["id"],
        "has_relevant_document": bool(relevant),
        "retrieval_recall_at_3": recall,
        "reciprocal_rank": reciprocal_rank,
        "abstention_correct": answer.abstained is bool(case["expect_abstain"]),
        "citation_valid": set(answer.cited_chunk_ids).issubset(retrieved_ids),
        "answer_term_recall": term_recall,
        "injection_exclusion_correct": answer.excluded_chunk_count == unsafe_retrieved,
    }


def evaluate(dataset_path: Path = DEFAULT_DATASET) -> EvaluationResult:
    raw = dataset_path.read_bytes()
    cases = load_cases(dataset_path)
    results = [evaluate_case(case) for case in cases]
    count = len(results)
    retrieval_results = [row for row in results if row["has_relevant_document"]]
    retrieval_count = len(retrieval_results)
    metrics = {
        "retrieval_recall_at_3": sum(
            row["retrieval_recall_at_3"] for row in retrieval_results
        )
        / retrieval_count,
        "mean_reciprocal_rank": sum(
            row["reciprocal_rank"] for row in retrieval_results
        )
        / retrieval_count,
        "abstention_accuracy": sum(row["abstention_correct"] for row in results) / count,
        "citation_validity": sum(row["citation_valid"] for row in results) / count,
        "answer_term_recall": sum(row["answer_term_recall"] for row in results) / count,
        "injection_exclusion_accuracy": sum(
            row["injection_exclusion_correct"] for row in results
        )
        / count,
    }
    return EvaluationResult(hashlib.sha256(raw).hexdigest(), count, metrics, results)


def threshold_failures(result: EvaluationResult, thresholds_path: Path) -> list[str]:
    thresholds = json.loads(thresholds_path.read_text(encoding="utf-8"))
    return [
        f"{metric}={result.metrics[metric]:.4f} is below {minimum:.4f}"
        for metric, minimum in thresholds.items()
        if result.metrics[metric] < minimum
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run deterministic RAG regression evaluation")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--thresholds", type=Path, default=DEFAULT_THRESHOLDS)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    result = evaluate(args.dataset)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result.as_dict(), indent=2) + "\n", encoding="utf-8")
    failures = threshold_failures(result, args.thresholds)
    print(json.dumps(result.metrics, indent=2))
    if args.check and failures:
        raise SystemExit("Evaluation thresholds failed: " + "; ".join(failures))


if __name__ == "__main__":
    main()
