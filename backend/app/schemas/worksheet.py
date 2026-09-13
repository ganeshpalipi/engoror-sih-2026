"""Pydantic schemas for the Phase 5 worksheet endpoints."""

from pydantic import BaseModel, Field

from app.services.content_data import NIPUN_NOTE

SKILLS = {"literacy", "numeracy"}
GRADES = {1, 2, 3}
COUNTS = {5, 10}


class WorksheetRequest(BaseModel):
    """Request body for POST /api/worksheets/generate."""

    grade: int = Field(..., description="Class level: 1, 2 or 3")
    skill: str = Field(..., description="'literacy' or 'numeracy'")
    topic: str = Field(..., description="Topic slug, e.g. 'animals' or 'numbers-1-10'")
    count: int = Field(default=5, description="Number of questions: 5 or 10")
    seed: int | None = Field(
        default=None,
        description="Optional deterministic seed; same seed = identical worksheet",
    )

    def validate_fields(self) -> list[str]:
        """Return human-friendly problems (kept out of pydantic errors so the
        teacher sees one clear message, not a stack of codes)."""
        problems: list[str] = []
        if self.grade not in GRADES:
            problems.append("Grade must be 1, 2 or 3.")
        if self.skill not in SKILLS:
            problems.append("Skill must be 'literacy' or 'numeracy'.")
        if self.count not in COUNTS:
            problems.append("Number of questions must be 5 or 10.")
        return problems


class WorksheetResponse(BaseModel):
    success: bool = True
    filename: str
    html_url: str = Field(description="Open this URL to preview / print the worksheet")
    download_url: str
    grade: int
    skill: str
    topic: str
    topic_label: str
    question_count: int
    types_included: list[str] = Field(
        description="Type letters used, e.g. ['A','C','D'] (see docs for the A-F legend)"
    )
    santali_available: bool = Field(
        description="False when the translation model is not ready - sheet is Hindi-only"
    )
    validation_notice: str = ""
    nipun_note: str = NIPUN_NOTE
    offline: bool = True


class WorksheetTopicInfo(BaseModel):
    skill: str
    topic: str
    label_hindi: str
    label_english: str


class WorksheetMetaResponse(BaseModel):
    grades: list[int]
    skills: list[str]
    counts: list[int]
    topics: list[WorksheetTopicInfo]
    type_legend: dict[str, str]
