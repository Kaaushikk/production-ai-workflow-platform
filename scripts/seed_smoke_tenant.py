import os

from sqlalchemy import select

from platform_api.auth import hash_api_key
from platform_api.config import get_settings
from platform_api.database import build_engine, build_session_factory
from platform_api.models import ApiKey, Tenant


def main() -> None:
    raw_key = os.environ["SMOKE_API_KEY"]
    factory = build_session_factory(build_engine(get_settings()))
    with factory.begin() as session:
        if session.scalar(select(Tenant).where(Tenant.slug == "ci-smoke")) is not None:
            return
        tenant = Tenant(slug="ci-smoke", name="CI Smoke")
        tenant.api_keys.append(
            ApiKey(
                name="ci-smoke",
                key_prefix=raw_key[:12],
                key_hash=hash_api_key(raw_key),
            )
        )
        session.add(tenant)


if __name__ == "__main__":
    main()
