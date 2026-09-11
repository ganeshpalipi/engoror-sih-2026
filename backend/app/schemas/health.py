"""Pydantic response schemas for the health endpoint."""

from pydantic import BaseModel, Field


class ComponentStatus(BaseModel):
    """Status of one system component (api, database, ...)."""

    status: str = Field(..., description='"ok" or "error"')
    detail: str = Field(default="", description="Human-friendly explanation")


class HealthResponse(BaseModel):
    """Response schema for GET /health."""

    status: str = Field(..., description='"ok" or "degraded"')
    app: str
    version: str
    offline_mode: bool
    components: dict[str, ComponentStatus]
