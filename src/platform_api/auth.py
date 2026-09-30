import hashlib
import secrets
import uuid
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select

from platform_api.dependencies import SessionDep
from platform_api.models import ApiKey, Tenant


def hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def generate_api_key() -> str:
    return f"pai_{secrets.token_urlsafe(32)}"


@dataclass(frozen=True)
class TenantContext:
    id: uuid.UUID
    slug: str


def require_tenant(
    x_api_key: Annotated[str, Header(alias="X-API-Key")],
    session: SessionDep,
) -> TenantContext:
    if not x_api_key.startswith("pai_") or len(x_api_key) < 20:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")

    key_hash = hash_api_key(x_api_key)
    row = session.execute(
        select(ApiKey, Tenant)
        .join(Tenant, Tenant.id == ApiKey.tenant_id)
        .where(ApiKey.key_hash == key_hash, ApiKey.revoked_at.is_(None))
    ).one_or_none()
    if row is None or not secrets.compare_digest(row.ApiKey.key_hash, key_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
    return TenantContext(id=row.Tenant.id, slug=row.Tenant.slug)


TenantDep = Annotated[TenantContext, Depends(require_tenant)]

