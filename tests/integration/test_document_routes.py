from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from platform_api.auth import hash_api_key
from platform_api.main import create_app
from platform_api.models import ApiKey, Base, Tenant

FIN_KEY = "pai_finserve_test_key_1234567890"
CLOUD_KEY = "pai_cloudops_test_key_1234567890"


@pytest.fixture
def tenant_client() -> Iterator[TestClient]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        for slug, name, raw_key in [
            ("finserve", "FinServe", FIN_KEY),
            ("cloudops", "CloudOps", CLOUD_KEY),
        ]:
            tenant = Tenant(slug=slug, name=name)
            tenant.api_keys.append(
                ApiKey(
                    name="test",
                    key_prefix=raw_key[:12],
                    key_hash=hash_api_key(raw_key),
                )
            )
            session.add(tenant)
        session.commit()

    with TestClient(create_app(engine_override=engine)) as client:
        yield client
    engine.dispose()


def test_document_upload_creates_chunks_and_supports_idempotent_retry(
    tenant_client: TestClient,
) -> None:
    headers = {"X-API-Key": FIN_KEY}
    files = {"file": ("policy.md", b"Policy one.\n\nPolicy two.", "text/markdown")}

    first = tenant_client.post("/v1/documents", headers=headers, files=files)
    duplicate = tenant_client.post("/v1/documents", headers=headers, files=files)

    assert first.status_code == 201
    assert first.json()["chunk_count"] == 1
    assert first.json()["status"] == "succeeded"
    assert first.json()["duplicate"] is False
    assert duplicate.status_code == 201
    assert duplicate.json()["id"] == first.json()["id"]
    assert duplicate.json()["duplicate"] is True


def test_tenant_cannot_read_another_tenants_document(tenant_client: TestClient) -> None:
    created = tenant_client.post(
        "/v1/documents",
        headers={"X-API-Key": FIN_KEY},
        files={"file": ("policy.txt", b"FinServe-only policy", "text/plain")},
    )
    document_id = created.json()["id"]

    response = tenant_client.get(
        f"/v1/documents/{document_id}", headers={"X-API-Key": CLOUD_KEY}
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Document not found"}


def test_same_content_is_stored_independently_for_each_tenant(
    tenant_client: TestClient,
) -> None:
    files = {"file": ("shared.txt", b"Shared public wording", "text/plain")}

    first = tenant_client.post("/v1/documents", headers={"X-API-Key": FIN_KEY}, files=files)
    second = tenant_client.post("/v1/documents", headers={"X-API-Key": CLOUD_KEY}, files=files)

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] != second.json()["id"]


def test_upload_requires_valid_api_key_and_supported_file(tenant_client: TestClient) -> None:
    missing_key = tenant_client.post(
        "/v1/documents", files={"file": ("policy.txt", b"text", "text/plain")}
    )
    invalid_file = tenant_client.post(
        "/v1/documents",
        headers={"X-API-Key": FIN_KEY},
        files={"file": ("policy.docx", b"text", "application/octet-stream")},
    )

    assert missing_key.status_code == 422
    assert invalid_file.status_code == 422
    assert "Only TXT, Markdown, and PDF" in invalid_file.json()["detail"]

