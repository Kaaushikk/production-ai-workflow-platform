import uuid
from datetime import UTC, datetime

from sqlalchemy import create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from outbox_dispatcher.dispatcher import dispatch_batch, retry_delay
from platform_api.events import EventEnvelope, EventType, enqueue_event
from platform_api.models import Base, OutboxEvent, Tenant


class RecordingPublisher:
    def __init__(self, *, fail: bool = False) -> None:
        self.events: list[EventEnvelope] = []
        self.fail = fail

    def publish(self, event: EventEnvelope) -> None:
        if self.fail:
            raise RuntimeError("broker offline")
        self.events.append(event)

    def close(self) -> None:
        pass


def create_outbox_database() -> tuple[Engine, uuid.UUID]:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    tenant = Tenant(slug="outbox-test", name="Outbox Test")
    with Session(engine) as session:
        session.add(tenant)
        session.commit()
        tenant_id = tenant.id
        enqueue_event(
            session,
            EventEnvelope(
                event_type=EventType.QUERY_COMPLETED,
                tenant_id=tenant_id,
                payload={"query_id": "query-1"},
            ),
        )
        session.commit()
    return engine, tenant_id


def test_dispatch_marks_confirmed_event_as_published() -> None:
    engine, _ = create_outbox_database()
    publisher = RecordingPublisher()
    now = datetime.now(UTC)

    with Session(engine) as session:
        result = dispatch_batch(session, publisher, now=now)
        stored = session.scalar(select(OutboxEvent))

    assert result == (1, 0)
    assert len(publisher.events) == 1
    assert stored is not None
    assert stored.published_at is not None
    assert stored.last_error is None


def test_dispatch_schedules_bounded_retry_after_failure() -> None:
    engine, _ = create_outbox_database()
    now = datetime.now(UTC)

    with Session(engine) as session:
        result = dispatch_batch(session, RecordingPublisher(fail=True), now=now)
        stored = session.scalar(select(OutboxEvent))

    assert result == (0, 1)
    assert stored is not None
    assert stored.attempts == 1
    assert stored.last_error == "RuntimeError: broker offline"
    assert stored.next_attempt_at.replace(tzinfo=UTC) == now + retry_delay(1)
    assert retry_delay(20).total_seconds() == 300


def test_outbox_event_rolls_back_with_its_domain_transaction() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    tenant = Tenant(slug="rollback-test", name="Rollback Test")
    with Session(engine) as session:
        session.add(tenant)
        session.commit()
        enqueue_event(
            session,
            EventEnvelope(
                event_type=EventType.DOCUMENT_INGESTED,
                tenant_id=tenant.id,
                payload={"document_id": "document-1"},
            ),
        )
        session.rollback()
        assert session.scalar(select(OutboxEvent)) is None
