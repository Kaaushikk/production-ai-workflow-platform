from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from platform_api.events import EventEnvelope
from platform_api.models import ProcessedEvent


def process_event(session: Session, event: EventEnvelope) -> bool:
    """Record an event exactly once from the worker's point of view.

    Returns True when this invocation processed the event and False for a replay.
    The unique database constraint also protects concurrent consumers.
    """

    if session.scalar(select(ProcessedEvent.id).where(ProcessedEvent.event_id == event.event_id)):
        return False

    session.add(
        ProcessedEvent(
            event_id=event.event_id,
            tenant_id=event.tenant_id,
            event_type=event.event_type,
            schema_version=event.schema_version,
            payload_json=event.payload,
        )
    )
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        if session.scalar(
            select(ProcessedEvent.id).where(ProcessedEvent.event_id == event.event_id)
        ):
            return False
        raise
    return True
