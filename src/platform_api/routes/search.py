from fastapi import APIRouter
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from platform_api.auth import TenantDep
from platform_api.dependencies import SessionDep
from platform_api.embeddings import default_embedding_provider
from platform_api.models import DocumentChunk
from platform_api.retrieval import Candidate, hybrid_rank
from platform_api.schemas import SearchRequest, SearchResponse, SearchResult

router = APIRouter(tags=["search"])


@router.post("/ai/search", response_model=SearchResponse)
def search_documents(
    request: SearchRequest,
    tenant: TenantDep,
    session: SessionDep,
) -> SearchResponse:
    chunks = session.scalars(
        select(DocumentChunk)
        .options(selectinload(DocumentChunk.document))
        .where(DocumentChunk.tenant_id == tenant.id, DocumentChunk.embedding.is_not(None))
    ).all()
    candidates = [
        Candidate(key=str(chunk.id), text=chunk.chunk_text, embedding=list(chunk.embedding or []))
        for chunk in chunks
    ]
    query_embedding = default_embedding_provider.embed([request.query])[0]
    ranked = hybrid_rank(request.query, query_embedding, candidates, request.limit)
    by_id = {str(chunk.id): chunk for chunk in chunks}
    results = [
        SearchResult(
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
    return SearchResponse(
        query=request.query,
        embedding_provider=default_embedding_provider.name,
        results=results,
    )

