"""
Worksheet endpoints (Phase 5).

GET  /api/worksheets/meta              Grades / skills / topics / type legend
POST /api/worksheets/generate          Build a printable bilingual worksheet
GET  /api/worksheets/file/{filename}   Serve the generated HTML (whitelist-only)

Files live under backend/generated_files/worksheets/ with names matching
`ws_<32 hex>.html` - the same whitelist approach as the Phase 4 TTS audio
endpoint, so no arbitrary file path can ever be fetched.
"""

import logging
import re

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.schemas.worksheet import (
    WorksheetMetaResponse,
    WorksheetRequest,
    WorksheetResponse,
    WorksheetTopicInfo,
)
from app.services.content_data import WORKSHEET_TOPICS
from app.services.worksheet_service import TYPE_LABELS, generate_worksheet

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/worksheets", tags=["Worksheets (Phase 5)"])

# Generated files are always named by the service: ws_<32 hex>.html
_SAFE_FILENAME = re.compile(r"^ws_[0-9a-f]{32}\.html$")


@router.get(
    "/meta",
    response_model=WorksheetMetaResponse,
    summary="Worksheet form metadata (grades, skills, topics, type legend)",
)
def worksheet_meta() -> WorksheetMetaResponse:
    return WorksheetMetaResponse(
        grades=[1, 2, 3],
        skills=["literacy", "numeracy"],
        counts=[5, 10],
        topics=[WorksheetTopicInfo(**t) for t in WORKSHEET_TOPICS],
        type_legend=dict(TYPE_LABELS),
    )


@router.post(
    "/generate",
    response_model=WorksheetResponse,
    summary="Generate a printable bilingual worksheet (offline, deterministic)",
)
def generate(payload: WorksheetRequest, db: Session = Depends(get_db)) -> WorksheetResponse:
    problems = payload.validate_fields()
    if problems:
        raise HTTPException(status_code=422, detail=" ".join(problems))

    valid_topics = {t["topic"] for t in WORKSHEET_TOPICS if t["skill"] == payload.skill}
    if payload.topic not in valid_topics:
        raise HTTPException(
            status_code=400,
            detail=(
                f"'{payload.topic}' is not a {payload.skill} topic. Please pick a topic "
                "from the worksheet form."
            ),
        )

    result = generate_worksheet(
        db,
        grade=payload.grade,
        skill=payload.skill,
        topic=payload.topic,
        count=payload.count,
        seed=payload.seed,
    )
    return WorksheetResponse(**result)


@router.get(
    "/file/{filename}",
    summary="Serve a generated worksheet HTML (whitelist: ws_<hex>.html)",
)
def serve_worksheet(filename: str, download: int = 0) -> Response:
    if not _SAFE_FILENAME.match(filename):
        raise HTTPException(
            status_code=404,
            detail="Worksheet not found. Please generate the worksheet again.",
        )
    path = settings.generated_files_path / "worksheets" / filename
    if not path.is_file():
        raise HTTPException(
            status_code=404,
            detail="This worksheet file has expired. Please generate it again.",
        )
    headers = {}
    if download:
        headers["Content-Disposition"] = f'attachment; filename="RootVerse-worksheet-{filename}"'
    return FileResponse(path, media_type="text/html", headers=headers)
