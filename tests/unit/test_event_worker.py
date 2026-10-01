import uuid

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from event_worker.handler import process_event
from platform_api.events import EventEnvelope, EventType
from platform_api.models import Base, ProcessedEvent, Tenant


def test_event_processing_is_idempotent() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    tenant = Tenant(slug="worker-test", name="Worker Test")
    with Session(engine) as session:
        session.add(tenant)
        session.commit()
        tenant_id = tenant.id

    event = EventEnvelope(
        event_type=EventType.DOCUMENT_INGESTED,
        tenant_id=tenant_id,
        payload={"document_id": str(uuid.uuid4()), "chunk_count": 2},
    )
    with Session(engine) as session:
        assert process_event(session, event) is True
        assert process_event(session, event) is False
        receipts = session.scalars(select(ProcessedEvent)).all()

    assert len(receipts) == 1
    assert receipts[0].event_id == event.event_id
    assert receipts[0].payload_json["chunk_count"] == 2
