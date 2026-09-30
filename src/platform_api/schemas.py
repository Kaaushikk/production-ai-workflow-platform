import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from platform_api.models import Document


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    service: str
    environment: str


class ReadinessResponse(BaseModel):
    status: Literal["ready"] = "ready"
    checks: dict[str, Literal["ok"]]


class ErrorResponse(BaseModel):
    detail: str


class DocumentResponse(BaseModel):
    id: uuid.UUID
    title: str
    source_filename: str
    media_type: str
    checksum: str
    chunk_count: int
    job_id: uuid.UUID
    status: str
    duplicate: bool = False

    @classmethod
    def from_model(cls, document: "Document", duplicate: bool = False) -> "DocumentResponse":
        return cls(
            id=document.id,
            title=document.title,
            source_filename=document.source_filename,
            media_type=document.media_type,
            checksum=document.checksum,
            chunk_count=len(document.chunks),
            job_id=document.ingestion_job.id,
            status=document.ingestion_job.status.value,
            duplicate=duplicate,
        )


class JobResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    document_id: uuid.UUID
    status: str
    error_code: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None


class SearchRequest(BaseModel):
    query: str = Field(min_length=2, max_length=500)
    limit: int = Field(default=5, ge=1, le=20)


class SearchResult(BaseModel):
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    title: str
    text: str
    vector_score: float
    lexical_score: float
    hybrid_score: float


class SearchResponse(BaseModel):
    query: str
    embedding_provider: str
    results: list[SearchResult]

