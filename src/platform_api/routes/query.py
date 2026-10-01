from time import perf_counter

from fastapi import APIRouter

from platform_api.answers import default_answer_provider
from platform_api.auth import TenantDep
from platform_api.dependencies import PublisherDep, SessionDep
from platform_api.events import EventEnvelope, EventType, publish_safely
from platform_api.models import QueryRecord
from platform_api.schemas import Citation, QueryRequest, QueryResponse
from platform_api.search_service import retrieve_chunks

router = APIRouter(tags=["query"])


@router.post("/ai/query", response_model=QueryResponse)
def answer_query(
    request: QueryRequest,
    tenant: TenantDep,
    session: SessionDep,
    publisher: PublisherDep,
) -> QueryResponse:
    started = perf_counter()
    evidence = retrieve_chunks(session, tenant.id, request.question, request.retrieval_limit)
    generated = default_answer_provider.answer(request.question, evidence)
    cited = set(generated.cited_chunk_ids)
    cited_evidence = [item for item in evidence if str(item.chunk_id) in cited]
    citations = [
        Citation(
            index=index,
            chunk_id=item.chunk_id,
            document_id=item.document_id,
            title=item.title,
        )
        for index, item in enumerate(cited_evidence, 1)
    ]
    latency_ms = max(0, round((perf_counter() - started) * 1000))
    record = QueryRecord(
        tenant_id=tenant.id,
        question=request.question,
        answer=generated.text,
        citations_json=[citation.model_dump(mode="json") for citation in citations],
        abstained=generated.abstained,
        provider_name=default_answer_provider.name,
        latency_ms=latency_ms,
    )
    session.add(record)
    session.commit()
    session.refresh(record)
    publish_safely(
        publisher,
        EventEnvelope(
            event_type=EventType.QUERY_COMPLETED,
            tenant_id=tenant.id,
            payload={
                "query_id": str(record.id),
                "abstained": record.abstained,
                "citation_count": len(citations),
                "latency_ms": latency_ms,
            },
        ),
    )
    return QueryResponse(
        query_id=record.id,
        answer=generated.text,
        citations=citations,
        abstained=generated.abstained,
        provider=default_answer_provider.name,
        excluded_unsafe_chunks=generated.excluded_chunk_count,
        latency_ms=latency_ms,
    )

