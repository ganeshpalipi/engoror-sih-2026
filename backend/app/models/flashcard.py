"""ORM model: flashcards — visual vocabulary cards for FLN practice (Phase 5).

Each card pairs a LOCAL visual (emoji and/or a bundled SVG asset in
frontend/public/flashcards/) with a Hindi word and its Santali (Ol Chiki)
translation. No external images are ever fetched at runtime.

SIH language rule: the Santali field is the placeholder
REQUIRES_LANGUAGE_VALIDATION until the existing IndicTrans2 service
translates it (validation_status then becomes AI_GENERATED). Text is never
invented by hand in this project.
"""

from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

REQUIRES_LANGUAGE_VALIDATION = "REQUIRES_LANGUAGE_VALIDATION"


class Flashcard(Base):
    __tablename__ = "flashcards"
    __table_args__ = (
        UniqueConstraint("topic", "hindi_word", name="uq_flashcard_topic_word"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    topic: Mapped[str] = mapped_column(String(40), default="general")
    hindi_word: Mapped[str] = mapped_column(String(100))
    english_word: Mapped[str] = mapped_column(String(100))
    # Local visual only: emoji character and/or key of a bundled SVG
    # (frontend/public/flashcards/<image_key>.svg). Never a remote URL.
    visual_emoji: Mapped[str] = mapped_column(String(16), default="")
    image_key: Mapped[str | None] = mapped_column(String(60), nullable=True)
    # Either a translated Santali string (AI_GENERATED) or the placeholder
    santhali_ol_chiki: Mapped[str] = mapped_column(String(200))
    validation_status: Mapped[str] = mapped_column(String(20), default="PLACEHOLDER")
    audio_path: Mapped[str | None] = mapped_column(String(300), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
