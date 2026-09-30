import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, status
from pydantic import BaseModel, Field

from inference_service.model import FEATURE_NAMES, LoadedModel


class MetricRow(BaseModel):
    cpu_percent: float = Field(ge=0, le=100)
    latency_ms: float = Field(ge=0)
    error_rate: float = Field(ge=0, le=1)
    request_rate: float = Field(ge=0)
    memory_percent: float = Field(ge=0, le=100)
    queue_depth: float = Field(ge=0)

    def as_features(self) -> list[float]:
        values = self.model_dump()
        return [float(values[name]) for name in FEATURE_NAMES]


class PredictionRequest(BaseModel):
    rows: list[MetricRow] = Field(min_length=1, max_length=100)


class PredictionResult(BaseModel):
    is_anomaly: bool
    score: float
    threshold: float


class PredictionResponse(BaseModel):
    model_version: str
    predictions: list[PredictionResult]


def create_app(model_path: Path | None = None) -> FastAPI:
    artifact_path = model_path or Path(
        os.getenv("MODEL_ARTIFACT_PATH", "artifacts/anomaly-autoencoder-v1.pt")
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.model = LoadedModel.from_path(artifact_path)
        yield

    app = FastAPI(title="Anomaly Inference Service", version="0.1.0", lifespan=lifespan)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/ready")
    def ready(request: Request) -> dict[str, str]:
        model: LoadedModel | None = getattr(request.app.state, "model", None)
        if model is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Model unavailable",
            )
        return {"status": "ready", "model_version": model.version}

    @app.post("/v1/predict", response_model=PredictionResponse)
    def predict(payload: PredictionRequest, request: Request) -> PredictionResponse:
        model: LoadedModel = request.app.state.model
        predictions = model.predict([row.as_features() for row in payload.rows])
        return PredictionResponse(
            model_version=model.version,
            predictions=[PredictionResult(**prediction.__dict__) for prediction in predictions],
        )

    return app


app = create_app()

