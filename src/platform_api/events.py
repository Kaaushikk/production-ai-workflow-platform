import logging
import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Protocol

from confluent_kafka import Producer
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from platform_api.models import OutboxEvent

logger = logging.getLogger(__name__)


class EventType(StrEnum):
    DOCUMENT_INGESTED = "document.ingested"
    QUERY_COMPLETED = "query.completed"
    TOOL_CALLED = "tool.called"
    ANOMALY_DETECTED = "anomaly.detected"
    EVALUATION_COMPLETED = "evaluation.completed"


class EventEnvelope(BaseModel):
    """Versioned contract shared by API producers and event workers."""

    model_config = ConfigDict(frozen=True)

    event_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    schema_version: int = Field(default=1, ge=1)
    event_type: EventType
    tenant_id: uuid.UUID
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    payload: dict[str, Any]


class EventPublisher(Protocol):
    def publish(self, event: EventEnvelope) -> None: ...

    def close(self) -> None: ...


class NullEventPublisher:
    """No-op publisher for development and tests without a broker."""

    def publish(self, event: EventEnvelope) -> None:
        del event

    def close(self) -> None:
        pass


class KafkaEventPublisher:
    def __init__(self, bootstrap_servers: str, topic: str) -> None:
        self._topic = topic
        self._producer = Producer(
            {
                "bootstrap.servers": bootstrap_servers,
                "enable.idempotence": True,
                "acks": "all",
            }
        )

    def publish(self, event: EventEnvelope) -> None:
        delivery_errors: list[str] = []

        def on_delivery(error: object | None, _: object) -> None:
            if error is not None:
                delivery_errors.append(str(error))

        self._producer.produce(
            self._topic,
            key=str(event.tenant_id),
            value=event.model_dump_json(),
            on_delivery=on_delivery,
        )
        remaining = self._producer.flush(10)
        if remaining:
            raise RuntimeError(f"Kafka delivery timed out for {remaining} event(s)")
        if delivery_errors:
            raise RuntimeError(f"Kafka delivery failed: {delivery_errors[0]}")

    def close(self) -> None:
        remaining = self._producer.flush(5)
        if remaining:
            logger.warning("kafka_events_not_flushed", extra={"remaining": remaining})


def build_event_publisher(bootstrap_servers: str, topic: str) -> EventPublisher:
    if not bootstrap_servers.strip():
        return NullEventPublisher()
    return KafkaEventPublisher(bootstrap_servers, topic)


def enqueue_event(session: Session, event: EventEnvelope) -> None:
    """Add an event to the current database transaction."""

    session.add(
        OutboxEvent(
            id=event.event_id,
            tenant_id=event.tenant_id,
            event_type=event.event_type,
            schema_version=event.schema_version,
            occurred_at=event.occurred_at,
            payload_json=event.payload,
        )
    )
