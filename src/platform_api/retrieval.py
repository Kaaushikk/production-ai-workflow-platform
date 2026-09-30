import math
import re
from collections import Counter
from dataclasses import dataclass

TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


@dataclass(frozen=True)
class Candidate:
    key: str
    text: str
    embedding: list[float]


@dataclass(frozen=True)
class RankedCandidate:
    candidate: Candidate
    vector_score: float
    lexical_score: float
    hybrid_score: float


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if len(left) != len(right):
        raise ValueError("Vectors must have matching dimensions")
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return sum(a * b for a, b in zip(left, right, strict=True)) / (left_norm * right_norm)


def bm25_scores(query: str, documents: list[str], k1: float = 1.5, b: float = 0.75) -> list[float]:
    tokenized = [TOKEN_PATTERN.findall(document.lower()) for document in documents]
    query_terms = set(TOKEN_PATTERN.findall(query.lower()))
    if not documents or not query_terms:
        return [0.0] * len(documents)
    average_length = sum(len(tokens) for tokens in tokenized) / len(tokenized) or 1.0
    document_frequency = {
        term: sum(1 for tokens in tokenized if term in set(tokens)) for term in query_terms
    }
    scores: list[float] = []
    for tokens in tokenized:
        counts = Counter(tokens)
        score = 0.0
        for term in query_terms:
            frequency = counts[term]
            if not frequency:
                continue
            inverse_frequency = math.log(
                1
                + (len(documents) - document_frequency[term] + 0.5)
                / (document_frequency[term] + 0.5)
            )
            denominator = frequency + k1 * (1 - b + b * len(tokens) / average_length)
            score += inverse_frequency * frequency * (k1 + 1) / denominator
        scores.append(score)
    return scores


def hybrid_rank(
    query: str,
    query_embedding: list[float],
    candidates: list[Candidate],
    limit: int,
    rrf_constant: int = 60,
) -> list[RankedCandidate]:
    if limit < 1:
        raise ValueError("limit must be positive")
    lexical = bm25_scores(query, [candidate.text for candidate in candidates])
    vector = [cosine_similarity(query_embedding, candidate.embedding) for candidate in candidates]
    vector_order = sorted(range(len(candidates)), key=lambda index: vector[index], reverse=True)
    lexical_order = sorted(range(len(candidates)), key=lambda index: lexical[index], reverse=True)
    vector_rank = {index: rank for rank, index in enumerate(vector_order, start=1)}
    lexical_rank = {index: rank for rank, index in enumerate(lexical_order, start=1)}
    combined = [
        1 / (rrf_constant + vector_rank[index]) + 1 / (rrf_constant + lexical_rank[index])
        for index in range(len(candidates))
    ]
    order = sorted(range(len(candidates)), key=lambda index: combined[index], reverse=True)
    return [
        RankedCandidate(candidates[index], vector[index], lexical[index], combined[index])
        for index in order[:limit]
    ]
