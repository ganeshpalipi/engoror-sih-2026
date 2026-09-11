"""ORM model: model_metadata — honest, real-time record of AI model load status."""

from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ModelMetadata(Base):
    """One row per AI model type ('mt', later 'asr', 'tts'). Updated by model_manager."""

    __tablename__ = "model_metadata"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    model_type: Mapped[str] = mapped_column(String(20), unique=True)
    model_name: Mapped[str] = mapped_column(String(160))
    direction: Mapped[str | None] = mapped_column(String(60), nullable=True)
    # not_loaded | loading | ready | error - mirrors ModelManager status
    status: Mapped[str] = mapped_column(String(20), default="not_loaded")
    device: Mapped[str | None] = mapped_column(String(20), nullable=True)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    loaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
