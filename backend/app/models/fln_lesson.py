"""ORM model: fln_lessons — foundational literacy & numeracy lessons (bilingual)."""

from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

REQUIRES_LANGUAGE_VALIDATION = "REQUIRES_LANGUAGE_VALIDATION"


class FlnLesson(Base):
    """FLN lesson aligned with NIPUN Bharat goals (no official certification claimed)."""

    __tablename__ = "fln_lessons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title_hindi: Mapped[str] = mapped_column(String(200))
    title_english: Mapped[str] = mapped_column(String(200))
    class_level: Mapped[int] = mapped_column(Integer, default=1)
    subject: Mapped[str] = mapped_column(String(40), default="literacy")
    # Phase 5 (additive): topic slug (e.g. "animals", "numbers-1-10") and the
    # specific FLN skill being practised. Existing databases get these columns
    # through the idempotent ALTER TABLE in services/content_seed.py.
    category: Mapped[str] = mapped_column(String(60), default="")
    skill: Mapped[str] = mapped_column(String(80), default="")
    hindi_text: Mapped[str] = mapped_column(Text)
    santhali_ol_chiki: Mapped[str] = mapped_column(Text)
    validation_status: Mapped[str] = mapped_column(String(20), default="PLACEHOLDER")
    learning_objective: Mapped[str] = mapped_column(Text)
    activity_instruction: Mapped[str] = mapped_column(Text)
    audio_path: Mapped[str | None] = mapped_column(String(300), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
