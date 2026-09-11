"""ORM model: classroom_phrases — bilingual classroom instruction pack."""

from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

# Value required for any Santali string that has not been reviewed by a
# native speaker. See datasets/README.md for the language-data policy.
REQUIRES_LANGUAGE_VALIDATION = "REQUIRES_LANGUAGE_VALIDATION"


class ClassroomPhrase(Base):
    __tablename__ = "classroom_phrases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    hindi: Mapped[str] = mapped_column(String(300))
    english: Mapped[str] = mapped_column(String(300))
    # Either a VERIFIED Santali string or the placeholder below - never invented text
    santhali_ol_chiki: Mapped[str] = mapped_column(String(300))
    validation_status: Mapped[str] = mapped_column(String(20), default="PLACEHOLDER")
    category: Mapped[str] = mapped_column(String(40), default="instruction")
    audio_path: Mapped[str | None] = mapped_column(String(300), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
