import json
import logging
import os
from typing import Any

from confluent_kafka import Consumer, KafkaError, KafkaException, Message, Producer
from pydantic import ValidationError

from event_worker.handler import process_event
from platform_api.config import Settings
from platform_api.database import build_engine, build_session_factory
from platform_api.events import EventEnvelope
from platform_api.logging import configure_logging

logger = logging.getLogger(__name__)


def dead_letter_payload(message: Message, error: Exception) -> bytes:
    value = message.value()
    raw_value = value.decode("utf-8", errors="replace") if value else ""
    body: dict[str, Any] = {
        "source_topic": message.topic(),
        "source_partition": message.partition(),
        "source_offset": message.offset(),
        "error_type": type(error).__name__,
        "error": str(error),
        "raw_value": raw_value,
    }
    return json.dumps(body).encode("utf-8")


def run() -> None:
    settings = Settings()
    configure_logging(settings.log_level)
    bootstrap_servers = settings.kafka_bootstrap_servers
    if not bootstrap_servers:
        raise RuntimeError("APP_KAFKA_BOOTSTRAP_SERVERS must be configured")

    group_id = os.getenv("EVENT_WORKER_GROUP_ID", "platform-event-worker-v1")
    dead_letter_topic = os.getenv("EVENT_WORKER_DLQ_TOPIC", f"{settings.kafka_topic}.dlq")
    consumer = Consumer(
        {
            "bootstrap.servers": bootstrap_servers,
            "group.id": group_id,
            "enable.auto.commit": False,
            "auto.offset.reset": "earliest",
        }
    )
    dead_letter_producer = Producer(
        {"bootstrap.servers": bootstrap_servers, "enable.idempotence": True, "acks": "all"}
    )
    engine = build_engine(settings)
    session_factory = build_session_factory(engine)
    consumer.subscribe([settings.kafka_topic])
    logger.info("event_worker_started", extra={"topic": settings.kafka_topic})

    try:
        while True:
            message = consumer.poll(1.0)
            if message is None:
                continue
            error = message.error()
            if error is not None:
                if error.code() == KafkaError._PARTITION_EOF:
                    continue
                raise KafkaException(error)

            try:
                value = message.value()
                if value is None:
                    raise ValueError("Event has an empty payload")
                event = EventEnvelope.model_validate_json(value)
                with session_factory() as session:
                    processed = process_event(session, event)
                logger.info(
                    "event_handled",
                    extra={"event_id": str(event.event_id), "processed": processed},
                )
            except (ValidationError, UnicodeDecodeError, ValueError) as exc:
                dead_letter_producer.produce(
                    dead_letter_topic,
                    key=message.key(),
                    value=dead_letter_payload(message, exc),
                )
                if dead_letter_producer.flush(5):
                    logger.error("dead_letter_publish_failed")
                    continue
                logger.warning("invalid_event_sent_to_dead_letter", exc_info=exc)
            except Exception:
                logger.exception("event_processing_failed")
                continue

            consumer.commit(message=message, asynchronous=False)
    except KeyboardInterrupt:
        logger.info("event_worker_stopping")
    finally:
        consumer.close()
        dead_letter_producer.flush(5)
        engine.dispose()


if __name__ == "__main__":
    run()
