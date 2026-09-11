"""ORM model: translation_history — every MT request (success or failure) is recorded here."""

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TranslationHistory(Base):
    """One row per translation request. Local-only data (SIH honesty + debugging)."""

    __tablename__ = "translation_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_language: Mapped[str] = mapped_column(String(20))
    target_language: Mapped[str] = mapped_column(String(20))
    input_text: Mapped[str] = mapped_column(Text)
    # NULL when the request failed - we never store a fake translation
    translated_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, index=True
    )
