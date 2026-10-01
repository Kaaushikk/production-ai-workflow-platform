from collections.abc import Iterator
from typing import Annotated, cast

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from platform_api.events import EventPublisher


def get_session(request: Request) -> Iterator[Session]:
    session = request.app.state.session_factory()
    try:
        yield session
    finally:
        session.close()


SessionDep = Annotated[Session, Depends(get_session)]


def get_event_publisher(request: Request) -> EventPublisher:
    return cast(EventPublisher, request.app.state.event_publisher)


PublisherDep = Annotated[EventPublisher, Depends(get_event_publisher)]

