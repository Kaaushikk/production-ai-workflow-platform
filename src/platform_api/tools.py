import uuid
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from platform_api.models import Document
from platform_api.search_service import retrieve_chunks

ArgsT = TypeVar("ArgsT", bound=BaseModel)


class ToolError(ValueError):
    pass


@dataclass(frozen=True)
class ToolContext:
    session: Session
    tenant_id: uuid.UUID


class Tool(Generic[ArgsT]):
    name: str
    args_model: type[ArgsT]

    def run(self, arguments: ArgsT, context: ToolContext) -> dict[str, Any]:
        raise NotImplementedError


class SearchDocumentsArgs(BaseModel):
    model_config = {"extra": "forbid"}

    query: str = Field(min_length=2, max_length=500)
    limit: int = Field(default=3, ge=1, le=5)


class SearchDocumentsTool(Tool[SearchDocumentsArgs]):
    name = "search_documents"
    args_model = SearchDocumentsArgs

    def run(self, arguments: SearchDocumentsArgs, context: ToolContext) -> dict[str, Any]:
        results = retrieve_chunks(
            context.session, context.tenant_id, arguments.query, arguments.limit
        )
        return {
            "results": [
                {
                    "chunk_id": str(item.chunk_id),
                    "document_id": str(item.document_id),
                    "title": item.title,
                    "text": item.text,
                }
                for item in results
            ]
        }


class CountDocumentsArgs(BaseModel):
    model_config = {"extra": "forbid"}


class CountDocumentsTool(Tool[CountDocumentsArgs]):
    name = "count_documents"
    args_model = CountDocumentsArgs

    def run(self, arguments: CountDocumentsArgs, context: ToolContext) -> dict[str, Any]:
        count = context.session.scalar(
            select(func.count())
            .select_from(Document)
            .where(Document.tenant_id == context.tenant_id)
        )
        return {"document_count": int(count or 0)}


class GetDocumentMetadataArgs(BaseModel):
    model_config = {"extra": "forbid"}

    document_id: uuid.UUID


class GetDocumentMetadataTool(Tool[GetDocumentMetadataArgs]):
    name = "get_document_metadata"
    args_model = GetDocumentMetadataArgs

    def run(self, arguments: GetDocumentMetadataArgs, context: ToolContext) -> dict[str, Any]:
        document = context.session.scalar(
            select(Document).where(
                Document.id == arguments.document_id,
                Document.tenant_id == context.tenant_id,
            )
        )
        if document is None:
            raise ToolError("Document not found")
        return {
            "document_id": str(document.id),
            "title": document.title,
            "source_filename": document.source_filename,
            "media_type": document.media_type,
        }


class ToolRegistry:
    def __init__(self, tools: list[Tool[Any]]) -> None:
        self._tools = {tool.name: tool for tool in tools}

    @property
    def names(self) -> list[str]:
        return sorted(self._tools)

    def execute(
        self, name: str, raw_arguments: dict[str, Any], context: ToolContext
    ) -> dict[str, Any]:
        tool = self._tools.get(name)
        if tool is None:
            raise ToolError("Tool is not allowed")
        try:
            arguments = tool.args_model.model_validate(raw_arguments)
        except ValidationError as exc:
            raise ToolError("Tool arguments are invalid") from exc
        return tool.run(arguments, context)


default_tool_registry = ToolRegistry(
    [SearchDocumentsTool(), CountDocumentsTool(), GetDocumentMetadataTool()]
)

