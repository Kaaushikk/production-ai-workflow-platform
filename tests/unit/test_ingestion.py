import hashlib

import pytest

from platform_api.ingestion import IngestionError, chunk_text, parse_document


def test_parse_text_normalizes_content_and_hashes_original_bytes() -> None:
    content = b"First  paragraph.\r\n\r\nSecond paragraph."

    parsed = parse_document("guide.md", content, "text/markdown")

    assert parsed.text == "First paragraph.\n\nSecond paragraph."
    assert parsed.checksum == hashlib.sha256(content).hexdigest()
    assert parsed.media_type == "text/markdown"


@pytest.mark.parametrize(
    ("filename", "content", "message"),
    [
        ("guide.docx", b"content", "Only TXT, Markdown, and PDF"),
        ("guide.txt", b"", "empty"),
        ("guide.txt", b"\xff", "UTF-8"),
    ],
)
def test_parse_document_rejects_invalid_uploads(
    filename: str, content: bytes, message: str
) -> None:
    with pytest.raises(IngestionError, match=message):
        parse_document(filename, content, None)


def test_chunk_text_preserves_content_with_overlap() -> None:
    text = "\n\n".join(["A" * 30, "B" * 30, "C" * 30])

    chunks = chunk_text(text, target_chars=50, overlap_chars=10)

    assert len(chunks) == 3
    assert chunks[0] == "A" * 30
    assert chunks[1].startswith("A" * 10)
    assert chunks[2].startswith("B" * 10)


def test_chunk_text_rejects_invalid_size_configuration() -> None:
    with pytest.raises(ValueError, match="target_chars"):
        chunk_text("text", target_chars=10, overlap_chars=10)

