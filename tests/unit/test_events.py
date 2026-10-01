import uuid
from datetime import UTC, datetime

from platform_api.events import EventEnvelope, EventType, publish_safely


class RecordingPublisher:
    def __init__(self, *, fail: bool = False) -> None:
        self.events: list[EventEnvelope] = []
        self.fail = fail

    def publish(self, event: EventEnvelope) -> None:
        if self.fail:
            raise RuntimeError("broker unavailable")
        self.events.append(event)

    def close(self) -> None:
        pass


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


def test_safe_publish_reports_success_and_contains_broker_failures() -> None:
    event = EventEnvelope(
        event_type=EventType.DOCUMENT_INGESTED,
        tenant_id=uuid.uuid4(),
        payload={"document_id": "document-1"},
    )
    recording = RecordingPublisher()

    assert publish_safely(recording, event) is True
    assert recording.events == [event]
    assert publish_safely(RecordingPublisher(fail=True), event) is False
