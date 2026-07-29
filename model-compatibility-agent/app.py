"""FastAPI entry point for the Model Compatibility Agent."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator

from compatibility_agent import CompatibilityAgent, CompatibilityResult
from device_database import list_device_names
from report_generator import render_report

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)
agent = CompatibilityAgent()


class CompatibilityRequest(BaseModel):
    """Validated input used to evaluate an edge deployment."""

    model_config = ConfigDict(str_strip_whitespace=True)

    model_name: str = Field(min_length=1, max_length=200, examples=["MobileNetV3-Large"])
    framework: str = Field(min_length=1, max_length=80, examples=["TensorFlow Lite"])
    model_size_mb: float = Field(gt=0, le=1_000_000, examples=[21.0])
    required_ram_gb: float = Field(gt=0, le=1_000, examples=[0.5])
    required_storage_gb: float = Field(gt=0, le=100_000, examples=[0.1])
    architecture: str = Field(min_length=1, max_length=80, examples=["ARM64"])
    edge_device: str = Field(min_length=1, max_length=120, examples=["Raspberry Pi 5"])

    @field_validator("model_name", "framework", "architecture", "edge_device")
    @classmethod
    def not_blank(cls, value: str) -> str:
        if not value:
            raise ValueError("must not be blank")
        return value


class CompatibilityResponse(BaseModel):
    """Machine-readable evaluation and its ready-to-display report."""

    compatibility: CompatibilityResult
    report: str


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("Model Compatibility Agent started; supported devices: %s", ", ".join(list_device_names()))
    yield
    logger.info("Model Compatibility Agent stopped")


app = FastAPI(
    title="Model Compatibility Agent",
    description="Edge AI Copilot Suite service for evaluating model/device compatibility.",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/check-compatibility", response_model=CompatibilityResponse)
async def check_compatibility(request: CompatibilityRequest) -> CompatibilityResponse:
    """Return an explainable score and report for a model/device pairing."""
    try:
        result = agent.evaluate(request.model_dump())
        return CompatibilityResponse(compatibility=result, report=render_report(result))
    except ValueError as exc:
        logger.warning("Compatibility request rejected: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - protects the API boundary
        logger.exception("Unexpected compatibility evaluation failure")
        raise HTTPException(status_code=500, detail="Unable to evaluate compatibility") from exc
