import uuid
from datetime import UTC, datetime

from platform_api.events import EventEnvelope, EventType


def test_event_envelope_round_trips_as_versioned_json() -> None:
    tenant_id = uuid.uuid4()
    event = EventEnvelope(
        event_type=EventType.QUERY_COMPLETED,
        tenant_id=tenant_id,
        occurred_at=datetime(2026, 9, 30, tzinfo=UTC),
        payload={"query_id": "query-1", "abstained": False},
    )

    restored = EventEnvelope.model_validate_json(event.model_dump_json())

    assert restored == event
    assert restored.schema_version == 1
