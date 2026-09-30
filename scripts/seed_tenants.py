from dataclasses import dataclass

from sqlalchemy import select

from platform_api.auth import generate_api_key, hash_api_key
from platform_api.config import get_settings
from platform_api.database import build_engine, build_session_factory
from platform_api.models import ApiKey, Tenant


@dataclass(frozen=True)
class TenantSeed:
    slug: str
    name: str


TENANTS = [TenantSeed("finserve", "FinServe"), TenantSeed("cloudops", "CloudOps")]


def main() -> None:
    factory = build_session_factory(build_engine(get_settings()))
    with factory.begin() as session:
        for seed in TENANTS:
            existing = session.scalar(select(Tenant).where(Tenant.slug == seed.slug))
            if existing is not None:
                print(f"{seed.slug}: already exists; no key created")
                continue
            raw_key = generate_api_key()
            tenant = Tenant(slug=seed.slug, name=seed.name)
            tenant.api_keys.append(
                ApiKey(
                    name="local-development",
                    key_prefix=raw_key[:12],
                    key_hash=hash_api_key(raw_key),
                )
            )
            session.add(tenant)
            print(f"{seed.slug}: {raw_key}")
    print("Save these development keys now; only their hashes are stored.")


if __name__ == "__main__":
    main()

