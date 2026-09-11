"""ORM model: asr_transcriptions — every Phase 3 speech-recognition request."""

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AsrTranscription(Base):
    """
    One row per ASR request (success or failure). Local-only data, used for
    debugging and honest latency records - never for cloud upload.
    """

    __tablename__ = "asr_transcriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    language: Mapped[str] = mapped_column(String(10), default="hi")
    # NULL when the request failed - we never store a fake transcript
    text: Mapped[str | None] = mapped_column(Text, nullable=True)
    audio_format: Mapped[str | None] = mapped_column(String(20), nullable=True)
    duration_sec: Mapped[float | None] = mapped_column(Float, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, index=True
    )
