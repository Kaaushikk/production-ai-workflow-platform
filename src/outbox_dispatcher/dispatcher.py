from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from platform_api.events import EventEnvelope, EventPublisher, EventType
from platform_api.models import OutboxEvent


def retry_delay(attempts: int) -> timedelta:
    return timedelta(seconds=min(2 ** max(0, attempts - 1), 300))


def dispatch_batch(
    session: Session,
    publisher: EventPublisher,
    *,
    batch_size: int = 50,
    now: datetime | None = None,
) -> tuple[int, int]:
    """Publish one locked batch and persist success or retry state."""

    current_time = now or datetime.now(UTC)
    events = session.scalars(
        select(OutboxEvent)
        .where(
            OutboxEvent.published_at.is_(None),
            OutboxEvent.next_attempt_at <= current_time,
        )
        .order_by(OutboxEvent.created_at, OutboxEvent.id)
        .limit(batch_size)
        .with_for_update(skip_locked=True)
    ).all()

    published = 0
    failed = 0
    for stored in events:
        event = EventEnvelope(
            event_id=stored.id,
            schema_version=stored.schema_version,
            event_type=EventType(stored.event_type),
            tenant_id=stored.tenant_id,
            occurred_at=stored.occurred_at,
            payload=stored.payload_json,
        )
        try:
            publisher.publish(event)
        except Exception as exc:
            stored.attempts += 1
            stored.last_error = f"{type(exc).__name__}: {exc}"[:500]
            stored.next_attempt_at = current_time + retry_delay(stored.attempts)
            failed += 1
        else:
            stored.published_at = current_time
            stored.last_error = None
            published += 1

    session.commit()
    return published, failed
