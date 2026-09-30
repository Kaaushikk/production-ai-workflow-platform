import hashlib
import io
import re
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader

MAX_UPLOAD_BYTES = 2 * 1024 * 1024
ALLOWED_SUFFIXES = {".txt", ".md", ".pdf"}


class IngestionError(ValueError):
    pass


@dataclass(frozen=True)
class ParsedDocument:
    text: str
    checksum: str
    media_type: str


def parse_document(
    filename: str, content: bytes, declared_media_type: str | None
) -> ParsedDocument:
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise IngestionError("Only TXT, Markdown, and PDF files are supported")
    if not content:
        raise IngestionError("The uploaded file is empty")
    if len(content) > MAX_UPLOAD_BYTES:
        raise IngestionError("The uploaded file exceeds the 2 MB limit")

    if suffix == ".pdf":
        try:
            pages = [page.extract_text() or "" for page in PdfReader(io.BytesIO(content)).pages]
        except Exception as exc:
            raise IngestionError("The PDF could not be parsed") from exc
        text = "\n\n".join(pages)
        media_type = "application/pdf"
    else:
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise IngestionError("Text files must use UTF-8 encoding") from exc
        media_type = declared_media_type or "text/plain"

    normalized = re.sub(r"[ \t]+", " ", text.replace("\r\n", "\n")).strip()
    if not normalized:
        raise IngestionError("No readable text was found")
    return ParsedDocument(
        text=normalized,
        checksum=hashlib.sha256(content).hexdigest(),
        media_type=media_type,
    )


def chunk_text(text: str, target_chars: int = 1400, overlap_chars: int = 160) -> list[str]:
    if target_chars <= overlap_chars or overlap_chars < 0:
        raise ValueError("target_chars must be greater than a non-negative overlap")
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        if current and len(current) + len(paragraph) + 2 > target_chars:
            chunks.append(current)
            prefix = current[-overlap_chars:] if overlap_chars else ""
            current = f"{prefix}\n\n{paragraph}".strip()
        else:
            current = f"{current}\n\n{paragraph}".strip()
        while len(current) > target_chars * 2:
            chunks.append(current[:target_chars])
            current = current[target_chars - overlap_chars :]
    if current:
        chunks.append(current)
    return chunks

