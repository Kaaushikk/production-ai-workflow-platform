import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from platform_api.config import get_settings
from platform_api.database import build_engine, build_session_factory, check_database
from platform_api.logging import configure_logging
from platform_api.routes.agent import router as agent_router
from platform_api.routes.documents import router as documents_router
from platform_api.routes.query import router as query_router
from platform_api.routes.search import router as search_router
from platform_api.schemas import ErrorResponse, HealthResponse, ReadinessResponse

logger = logging.getLogger(__name__)


def create_app(*, engine_override: Engine | None = None) -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)
    engine = engine_override or build_engine(settings)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        logger.info("application_started")
        yield
        engine.dispose()
        logger.info("application_stopped")

    app = FastAPI(
        title=settings.name,
        version="0.1.0",
        lifespan=lifespan,
        responses={status.HTTP_503_SERVICE_UNAVAILABLE: {"model": ErrorResponse}},
    )
    app.state.settings = settings
    app.state.engine = engine
    app.state.session_factory = build_session_factory(engine)
    app.include_router(agent_router, prefix="/v1")
    app.include_router(documents_router, prefix="/v1")
    app.include_router(query_router, prefix="/v1")
    app.include_router(search_router, prefix="/v1")

    @app.exception_handler(SQLAlchemyError)
    async def database_error_handler(_: Request, exc: SQLAlchemyError) -> JSONResponse:
        logger.error("database_operation_failed", exc_info=exc)
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"detail": "Database unavailable"},
        )

    @app.get("/health", response_model=HealthResponse, tags=["system"])
    def health() -> HealthResponse:
        return HealthResponse(service=settings.name, environment=settings.env)

    @app.get(
        "/ready",
        response_model=ReadinessResponse,
        responses={status.HTTP_503_SERVICE_UNAVAILABLE: {"model": ErrorResponse}},
        tags=["system"],
    )
    def ready() -> ReadinessResponse:
        try:
            check_database(engine)
        except SQLAlchemyError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database unavailable",
            ) from exc
        return ReadinessResponse(checks={"database": "ok"})

    return app


app = create_app()

