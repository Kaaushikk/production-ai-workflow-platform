from fastapi import APIRouter

from platform_api.auth import TenantDep
from platform_api.dependencies import SessionDep
from platform_api.embeddings import default_embedding_provider
from platform_api.rate_limit import RateLimitDep
from platform_api.schemas import SearchRequest, SearchResponse, SearchResult
from platform_api.search_service import retrieve_chunks

router = APIRouter(tags=["search"])


@router.post("/ai/search", response_model=SearchResponse)
def search_documents(
    request: SearchRequest,
    tenant: TenantDep,
    session: SessionDep,
    _rate_limit: RateLimitDep,
) -> SearchResponse:
    ranked = retrieve_chunks(session, tenant.id, request.query, request.limit)
    results = [
        SearchResult(
            chunk_id=item.chunk_id,
            document_id=item.document_id,
            title=item.title,
            text=item.text,
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

