import pytest

from platform_api.embeddings import EMBEDDING_DIMENSION, HashEmbeddingProvider
from platform_api.retrieval import Candidate, bm25_scores, cosine_similarity, hybrid_rank


def test_hash_embeddings_are_deterministic_normalized_and_sized() -> None:
    provider = HashEmbeddingProvider()

    first, second = provider.embed(["payment failure", "payment failure"])

    assert first == second
    assert len(first) == EMBEDDING_DIMENSION
    assert cosine_similarity(first, first) == pytest.approx(1.0)


def test_bm25_prefers_document_with_query_terms() -> None:
    scores = bm25_scores("payment timeout", ["payment timeout retry", "cloud deployment guide"])

    assert scores[0] > scores[1]


def test_hybrid_rank_combines_vector_and_lexical_order() -> None:
    provider = HashEmbeddingProvider()
    texts = ["payment failure timeout", "database backup policy", "payment success report"]
    vectors = provider.embed(texts)
    candidates = [
        Candidate(key=str(index), text=text, embedding=vector)
        for index, (text, vector) in enumerate(zip(texts, vectors, strict=True))
    ]

    results = hybrid_rank(
        "payment timeout", provider.embed(["payment timeout"])[0], candidates, limit=2
    )

    assert results[0].candidate.key == "0"
    assert len(results) == 2
    assert results[0].hybrid_score >= results[1].hybrid_score


def test_cosine_similarity_rejects_dimension_mismatch() -> None:
    with pytest.raises(ValueError, match="matching dimensions"):
        cosine_similarity([1.0], [1.0, 2.0])

