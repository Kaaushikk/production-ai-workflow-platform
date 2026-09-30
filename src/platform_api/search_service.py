import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from platform_api.embeddings import default_embedding_provider
from platform_api.models import DocumentChunk
from platform_api.retrieval import Candidate, hybrid_rank


@dataclass(frozen=True)
class RetrievedChunk:
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    title: str
    text: str
    vector_score: float
    lexical_score: float
    hybrid_score: float


def retrieve_chunks(
    session: Session, tenant_id: uuid.UUID, query: str, limit: int
) -> list[RetrievedChunk]:
    chunks = session.scalars(
        select(DocumentChunk)
        .options(selectinload(DocumentChunk.document))
        .where(DocumentChunk.tenant_id == tenant_id, DocumentChunk.embedding.is_not(None))
    ).all()
    candidates = [
        Candidate(key=str(chunk.id), text=chunk.chunk_text, embedding=list(chunk.embedding or []))
        for chunk in chunks
    ]
    ranked = hybrid_rank(
        query,
        default_embedding_provider.embed([query])[0],
        candidates,
        limit,
    )
    by_id = {str(chunk.id): chunk for chunk in chunks}
    return [
        RetrievedChunk(
            chunk_id=by_id[item.candidate.key].id,
            document_id=by_id[item.candidate.key].document_id,
            title=by_id[item.candidate.key].document.title,
            text=item.candidate.text,
            vector_score=item.vector_score,
            lexical_score=item.lexical_score,
            hybrid_score=item.hybrid_score,
        )
        for item in ranked
    ]

