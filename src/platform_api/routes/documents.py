import uuid
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from platform_api.auth import TenantDep
from platform_api.dependencies import SessionDep
from platform_api.ingestion import IngestionError, chunk_text, parse_document
from platform_api.models import Document, DocumentChunk, IngestionJob, IngestionStatus, utc_now
from platform_api.schemas import DocumentResponse, JobResponse

router = APIRouter(tags=["documents"])


@router.post("/documents", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: Annotated[UploadFile, File()],
    tenant: TenantDep,
    session: SessionDep,
    title: Annotated[str | None, Form(max_length=300)] = None,
) -> DocumentResponse:
    filename = file.filename or "upload"
    try:
        parsed = parse_document(filename, await file.read(), file.content_type)
    except IngestionError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc

    existing = session.scalar(
        select(Document).where(
            Document.tenant_id == tenant.id,
            Document.checksum == parsed.checksum,
        )
    )
    if existing is not None:
        return DocumentResponse.from_model(existing, duplicate=True)

    document = Document(
        tenant_id=tenant.id,
        title=(title or filename).strip(),
        source_filename=filename,
        media_type=parsed.media_type,
        checksum=parsed.checksum,
    )
    job = IngestionJob(
        document=document,
        tenant_id=tenant.id,
        status=IngestionStatus.PROCESSING,
        started_at=utc_now(),
    )
    for ordinal, text in enumerate(chunk_text(parsed.text)):
        document.chunks.append(
            DocumentChunk(
                tenant_id=tenant.id,
                ordinal=ordinal,
                chunk_text=text,
                metadata_json={"source_filename": filename},
            )
        )
    job.status = IngestionStatus.SUCCEEDED
    job.completed_at = utc_now()
    session.add(document)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        duplicate = session.scalar(
            select(Document).where(
                Document.tenant_id == tenant.id,
                Document.checksum == parsed.checksum,
            )
        )
        if duplicate is None:
            raise exc
        return DocumentResponse.from_model(duplicate, duplicate=True)
    session.refresh(document)
    return DocumentResponse.from_model(document)


@router.get("/documents/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: uuid.UUID,
    tenant: TenantDep,
    session: SessionDep,
) -> DocumentResponse:
    document = session.scalar(
        select(Document).where(Document.id == document_id, Document.tenant_id == tenant.id)
    )
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return DocumentResponse.from_model(document)


@router.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(
    job_id: uuid.UUID,
    tenant: TenantDep,
    session: SessionDep,
) -> JobResponse:
    job = session.scalar(
        select(IngestionJob).where(
            IngestionJob.id == job_id, IngestionJob.tenant_id == tenant.id
        )
    )
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return JobResponse.model_validate(job)

