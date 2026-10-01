import logging
import os
import time

from outbox_dispatcher.dispatcher import dispatch_batch
from platform_api.config import Settings
from platform_api.database import build_engine, build_session_factory
from platform_api.events import build_event_publisher
from platform_api.logging import configure_logging

logger = logging.getLogger(__name__)


def run() -> None:
    settings = Settings()
    configure_logging(settings.log_level)
    if not settings.kafka_bootstrap_servers:
        raise RuntimeError("APP_KAFKA_BOOTSTRAP_SERVERS must be configured")

    poll_seconds = float(os.getenv("OUTBOX_POLL_SECONDS", "1"))
    batch_size = int(os.getenv("OUTBOX_BATCH_SIZE", "50"))
    engine = build_engine(settings)
    session_factory = build_session_factory(engine)
    publisher = build_event_publisher(settings.kafka_bootstrap_servers, settings.kafka_topic)
    logger.info("outbox_dispatcher_started", extra={"topic": settings.kafka_topic})

    try:
        while True:
            with session_factory() as session:
                published, failed = dispatch_batch(session, publisher, batch_size=batch_size)
            if published or failed:
                logger.info(
                    "outbox_batch_finished",
                    extra={"published": published, "failed": failed},
                )
            if published == 0:
                time.sleep(poll_seconds)
    except KeyboardInterrupt:
        logger.info("outbox_dispatcher_stopping")
    finally:
        publisher.close()
        engine.dispose()


if __name__ == "__main__":
    run()
