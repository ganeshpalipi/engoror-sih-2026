"""
Seed service: fills empty tables with safe development data.

SIH language rule (see datasets/README.md):
  - NO Santali text is invented here.
  - Every Santali field is the placeholder REQUIRES_LANGUAGE_VALIDATION with
    validation_status = PLACEHOLDER until a native speaker reviews it.
Seeding is idempotent: it only runs when a table is empty.
"""

import logging

from sqlalchemy.orm import Session

from app.models import (
    REQUIRES_LANGUAGE_VALIDATION,
    ClassroomPhrase,
    FlnLesson,
    ModelMetadata,
)

logger = logging.getLogger(__name__)


def _seed_phrases(db: Session) -> int:
    if db.query(ClassroomPhrase).count() > 0:
        return 0
    rows = [
        ClassroomPhrase(hindi="अपनी किताब खोलो।", english="Open your book.", category="instruction"),
        ClassroomPhrase(hindi="कक्षा में शांत रहो।", english="Keep quiet in the classroom.", category="instruction"),
        ClassroomPhrase(hindi="सब लोग खड़े हो जाओ।", english="Everyone, stand up.", category="instruction"),
        ClassroomPhrase(hindi="ध्यान से सुनो।", english="Listen carefully.", category="instruction"),
        ClassroomPhrase(hindi="मेरे बाद दोहराओ।", english="Repeat after me.", category="instruction"),
        ClassroomPhrase(hindi="एक से दस तक गिनो।", english="Count from one to ten.", category="activity"),
        ClassroomPhrase(hindi="बहुत अच्छा किया!", english="Well done!", category="praise"),
        ClassroomPhrase(hindi="अपना नाम लिखो।", english="Write your name.", category="instruction"),
    ]
    for row in rows:
        row.santhali_ol_chiki = REQUIRES_LANGUAGE_VALIDATION
        row.validation_status = "PLACEHOLDER"
        row.audio_path = None
    db.add_all(rows)
    return len(rows)


def _seed_lessons(db: Session) -> int:
    if db.query(FlnLesson).count() > 0:
        return 0
    rows = [
        FlnLesson(
            title_hindi="गिनती: एक से दस",
            title_english="Numbers: One to Ten",
            class_level=1,
            subject="numeracy",
            hindi_text="आज हम एक से दस तक गिनती सीखेंगे।",
            learning_objective="Student counts aloud from 1 to 10 and shows numbers on fingers.",
            activity_instruction="सभी विद्यार्थी मिलकर एक से दस तक गिनें और उंगलियों से संख्या दिखाएँ।",
        ),
        FlnLesson(
            title_hindi="वर्णमाला परिचय",
            title_english="Introduction to the Alphabet",
            class_level=1,
            subject="literacy",
            hindi_text="आज हम कुछ पहले अक्षर पहचानेंगे।",
            learning_objective="Student recognizes and says the first letters of the Hindi alphabet.",
            activity_instruction="शिक्षक अक्षर दिखाएँ; विद्यार्थी मिलकर बोलें और हवा में लिखें।",
        ),
        FlnLesson(
            title_hindi="आकार: गोल, त्रिकोण, चौकोर",
            title_english="Shapes: Circle, Triangle, Square",
            class_level=1,
            subject="numeracy",
            hindi_text="आज हम आकार पहचानेंगे।",
            learning_objective="Student names circle, triangle and square.",
            activity_instruction="कक्षा में गोल, त्रिकोण और चौकोर चीज़ें ढूँढो और नाम बताओ।",
        ),
        FlnLesson(
            title_hindi="रंग पहचानो",
            title_english="Recognize Colors",
            class_level=1,
            subject="literacy",
            hindi_text="आज हम रंगों के नाम सीखेंगे।",
            learning_objective="Student names common colors found in the classroom.",
            activity_instruction="कक्षा की चीज़ों के रंग बताओ और मिलकर दोहराओ।",
        ),
    ]
    for row in rows:
        row.santhali_ol_chiki = REQUIRES_LANGUAGE_VALIDATION
        row.validation_status = "PLACEHOLDER"
        row.audio_path = None
    db.add_all(rows)
    return len(rows)


def _seed_model_metadata(db: Session) -> int:
    if db.query(ModelMetadata).count() > 0:
        return 0
    from app.config import settings

    db.add(
        ModelMetadata(
            model_type="mt",
            model_name=settings.MT_MODEL_ID,
            direction=f"{'hin_Deva'} -> {'sat_Olck'}",
            status="not_loaded",
        )
    )
    return 1


def seed_if_empty() -> dict:
    """Insert development seed data into any empty table. Returns seeded counts."""
    from app.database import SessionLocal

    seeded: dict[str, int] = {}
    try:
        with SessionLocal() as db:
            phrases = _seed_phrases(db)
            lessons = _seed_lessons(db)
            metadata = _seed_model_metadata(db)
            db.commit()
        if phrases:
            seeded["classroom_phrases"] = phrases
        if lessons:
            seeded["fln_lessons"] = lessons
        if metadata:
            seeded["model_metadata"] = metadata
        if seeded:
            logger.info("Seeded database: %s", seeded)
    except Exception:
        # A seed failure must not prevent the API from starting (health shows DB state)
        logger.exception("Database seeding failed (non-fatal)")
    return seeded
