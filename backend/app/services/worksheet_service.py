"""
Offline bilingual worksheet generator (Phase 5).

Deterministic, content-driven, and fully offline: questions are built from
the FLN lesson bank / classroom phrases / flashcards stored in SQLite and
use LOCAL emoji + bundled SVG names only. No LLM, no cloud API, no online
images, no invented facts.

Worksheet types (exactly the six requested for the prototype):
  A  match the word        (Hindi <-> Santali pairs)
  B  fill in the blank     (number sequences or a missing word in the lesson sentence)
  C  count the objects     (emoji groups -> numeral)
  D  choose the correct answer (arithmetic, comparison, next-number,
                              shape names, patterns, picture MCQ)
  E  picture -> word       (emoji -> write the Hindi word)
  F  Hindi -> Santali vocabulary practice

Santali on worksheets:
  - Santali words come ONLY from the existing IndicTrans2 translation
    service (Phase 2). When a flashcard has no translation yet, the
    generator translates the missing words once and stores them back on the
    flashcard row. Lesson-sentence words and instruction lines are
    translated on the fly (small batched calls, not persisted).
  - If the translation model is unavailable (e.g. not downloaded yet), the
    worksheet is still generated - Hindi-only - with santali_available=False
    and a clear notice. Nothing is ever faked.

Determinism: the same (grade, skill, topic, count, seed) always produces the
same worksheet, so a teacher can regenerate/print the identical sheet.
Without an explicit seed, a stable per-topic default seed is used.

Output: a self-contained printable HTML file (no external requests) under
backend/generated_files/worksheets/, with the Ol Chiki font embedded as a
base64 data-URI so the script renders even fully offline. Printing to PDF
is done by the browser (File -> Print) which shapes Devanagari and Ol Chiki
correctly with zero extra dependencies.
"""

import hashlib
import html
import logging
import random
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy.orm import Session

from app.ai.translation_service import TranslationModelError
from app.config import settings
from app.models import Flashcard, FlnLesson
from app.services import content_service
from app.services.content_data import (
    NIPUN_NOTE,
    VALIDATION_NOTICE,
    worksheet_topic_label,
)

logger = logging.getLogger(__name__)

# Number of worksheet files kept on disk (housekeeping, mirrors TTS policy)
KEEP_FILES = 30

# Type letters shown to teachers (matches the SIH Phase 5 spec)
TYPE_MATCH = "A"
TYPE_FILL_BLANK = "B"
TYPE_COUNT = "C"
TYPE_MCQ = "D"
TYPE_PICTURE_WORD = "E"
TYPE_VOCAB_PRACTICE = "F"
TYPE_LABELS = {
    TYPE_MATCH: "Match the word",
    TYPE_FILL_BLANK: "Fill in the blank",
    TYPE_COUNT: "Count the objects",
    TYPE_MCQ: "Choose the correct answer",
    TYPE_PICTURE_WORD: "Picture -> word",
    TYPE_VOCAB_PRACTICE: "Hindi -> Santali vocabulary practice",
}

# Standard instruction lines (Hindi) that get translated once per worksheet
INSTR_COUNT = "गिनो और सही संख्या लिखो।"
INSTR_FILL_NUM = "खाली जगह में सही संख्या लिखो।"
INSTR_MCQ = "सही उत्तर पर गोला लगाओ।"
INSTR_PICTURE = "चित्र देखो और शब्द लिखो।"
INSTR_MATCH = "हिंदी शब्द को संताली शब्द से मिलाओ।"
INSTR_VOCAB = "हर हिंदी शब्द के आगे संताली (ᱚᱞ ᱪᱤᱠᱤ) शब्द लिखो।"
INSTR_FILL_WORD = "वाक्य में सही शब्द लिखो।"

# Local, deterministic countable emojis for counting/addition questions
COUNTABLE_EMOJI = ["🍎", "🍌", "✏️", "📖", "⭐", "🔴", "🟢", "🐱"]

# Fonts embedded into every worksheet (copied into backend/app/static/fonts)
_FONT_DIR = Path(__file__).resolve().parent.parent / "static" / "fonts"
_FONT_FILES = {
    "olchiki": _FONT_DIR / "NotoSansOlChiki-olchiki.woff2",
    "latin": _FONT_DIR / "NotoSansOlChiki-latin.woff2",
}

# In-memory cache for translated instruction lines (small, per process)
_INSTR_CACHE: dict[str, str] = {}


@dataclass
class Question:
    qtype: str                       # A..F type letter
    instruction_hindi: str
    instruction_santali: str | None = None   # Santali instruction line (when MT is available)
    body_hindi: str = ""
    santali: str | None = None       # Santali shown with the question (or None)
    visual: str | None = None        # emoji visual (repeated for counting)
    options: list[str] = field(default_factory=list)
    answer: str = ""                 # plain-text answer for the teacher key
    # match / vocab-practice use (hindi, santali) rows instead of options
    match_pairs: list[tuple[str, str]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Translation helpers (reuse the existing Phase 2 service)
# ---------------------------------------------------------------------------

def _translate_missing_flashcards(db: Session, cards: list[Flashcard]) -> bool:
    """
    Fill placeholder flashcard translations via the MT service.

    Returns True when the resulting sheet will contain Santali content:
    either everything got translated, or at least one card already carries a
    translation (partial coverage still shows the Santali it has - the
    missing words simply stay Hindi-only on the sheet).
    """
    pending = [c for c in cards if content_service._is_pending(c)]
    if pending:
        try:
            lines = [c.hindi_word for c in pending]
            translated, _meta = content_service.translate_lines_batched(lines)
        except TranslationModelError as exc:
            logger.info("Worksheet: flashcard translation unavailable (%s)", exc.user_message)
        else:
            for card, santali in zip(pending, translated):
                if santali.strip():
                    card.santhali_ol_chiki = santali.strip()
                    card.validation_status = content_service.AI_GENERATED
            db.commit()
    has_any = any(
        c.validation_status == content_service.AI_GENERATED and c.santhali_ol_chiki
        for c in cards
    )
    return has_any


def _translate_words(words: list[str]) -> dict[str, str] | None:
    """Translate short Hindi words on the fly; None when MT is unavailable."""
    unique = [w for w in dict.fromkeys(words) if w]
    if not unique:
        return {}
    try:
        translated, _meta = content_service.translate_lines_batched(unique)
    except TranslationModelError:
        return None
    mapping = {}
    for word, santali in zip(unique, translated):
        if santali.strip():
            mapping[word] = santali.strip()
    return mapping


def _translated_instructions() -> dict[str, str]:
    """Translate the standard instruction lines once (cached in memory)."""
    todo = [s for s in {INSTR_COUNT, INSTR_FILL_NUM, INSTR_MCQ, INSTR_PICTURE,
                        INSTR_MATCH, INSTR_VOCAB, INSTR_FILL_WORD} if s not in _INSTR_CACHE]
    if todo:
        mapping = _translate_words(todo)
        if mapping:
            _INSTR_CACHE.update(mapping)
    return dict(_INSTR_CACHE)


# ---------------------------------------------------------------------------
# Content pool
# ---------------------------------------------------------------------------

@dataclass
class TopicPool:
    topic: str
    label: str
    grade: int
    lesson: FlnLesson | None
    cards: list[Flashcard] = field(default_factory=list)
    sentence_words: list[str] = field(default_factory=list)


_FLASHCARD_TOPIC_BY_WORKSHEET_TOPIC = {
    "numbers-1-10": "numbers",
    "numbers-11-20": "numbers",
    "classroom-objects": "classroom-objects",
}


def _build_pool(db: Session, grade: int, skill: str, topic: str) -> TopicPool:
    pool = TopicPool(topic=topic, label=worksheet_topic_label(topic), grade=grade, lesson=None)

    lesson = (
        db.query(FlnLesson)
        .filter(FlnLesson.category == topic, FlnLesson.subject == skill)
        .first()
    )
    if lesson is None:  # fall back to any lesson of the category
        lesson = db.query(FlnLesson).filter(FlnLesson.category == topic).first()
    pool.lesson = lesson

    flash_topic = _FLASHCARD_TOPIC_BY_WORKSHEET_TOPIC.get(topic, topic)
    cards = (
        db.query(Flashcard)
        .filter(Flashcard.topic == flash_topic)
        .order_by(Flashcard.id)
        .all()
    )
    if flash_topic == "numbers" and topic == "numbers-11-20":
        cards = []  # 11-20 has no flashcards; arithmetic-only worksheet
    pool.cards = list(cards)

    if lesson is not None:
        seen: set[str] = set()
        for token in lesson.hindi_text.split():
            word = token.strip("।.,?!(\"')—-")
            if word and word not in seen:
                seen.add(word)
                pool.sentence_words.append(word)
    return pool


# ---------------------------------------------------------------------------
# Question builders (each returns built questions; skips itself gracefully)
# ---------------------------------------------------------------------------

def _number_range(topic: str, grade: int) -> tuple[int, int]:
    if topic == "numbers-11-20":
        return 11, 20
    if topic in {"addition", "subtraction"}:
        return (1, 10) if grade <= 1 else (1, 20)
    return 1, 10


def _build_count(pool: TopicPool, rng, n: int) -> list[Question]:
    lo, hi = _number_range(pool.topic, pool.grade)
    hi = min(hi, 10)  # emoji groups stay readable
    out: list[Question] = []
    for _ in range(n):
        emoji = rng.choice(COUNTABLE_EMOJI)
        total = rng.randint(lo, hi)
        out.append(Question(
            qtype=TYPE_COUNT,
            instruction_hindi=INSTR_COUNT,
            visual=emoji,
            body_hindi=f"{emoji} " * total,
            answer=str(total),
        ))
    return out


def _build_fill_sequence(pool: TopicPool, rng, n: int) -> list[Question]:
    lo, hi = _number_range(pool.topic, pool.grade)
    out: list[Question] = []
    for _ in range(n):
        start = rng.randint(lo, hi - 3)
        seq = list(range(start, start + 4))
        blank_idx = rng.randint(1, 2)
        answer = seq[blank_idx]
        shown = [str(x) for x in seq]
        shown[blank_idx] = "____"
        out.append(Question(
            qtype=TYPE_FILL_BLANK,
            instruction_hindi=INSTR_FILL_NUM,
            body_hindi=" ,  ".join(shown),
            answer=str(answer),
        ))
    return out


def _build_mcq_arith(pool: TopicPool, rng, n: int) -> list[Question]:
    lo, hi = _number_range(pool.topic, pool.grade)
    subtraction = pool.topic == "subtraction"
    addition = pool.topic == "addition"
    out: list[Question] = []
    for _ in range(n):
        if addition or (pool.topic in {"numbers-1-10", "numbers-11-20"} and rng.random() < 0.5):
            a = rng.randint(lo, min(hi - 1, 9))
            b = rng.randint(1, min(hi - a, 9))
            answer = a + b
            body = f"{a} + {b} = ?"
        elif subtraction:
            a = rng.randint(max(2, lo + 1), hi)
            b = rng.randint(1, a - 1)
            answer = a - b
            body = f"{a} − {b} = ?"
        else:
            a = rng.randint(lo, hi - 1)
            answer = a + 1
            body = f"{a} के बाद कौन सी संख्या आती है?"
        options = _number_options(answer, rng, hi + 4)
        out.append(Question(
            qtype=TYPE_MCQ,
            instruction_hindi=INSTR_MCQ,
            body_hindi=body,
            options=options,
            answer=str(answer),
        ))
    return out


def _number_options(answer: int, rng, max_val: int) -> list[str]:
    options = {answer}
    while len(options) < 3:
        delta = rng.choice([-3, -2, -1, 1, 2, 3])
        candidate = answer + delta
        if 0 < candidate <= max_val:
            options.add(candidate)
    values = list(options)
    rng.shuffle(values)
    return [str(v) for v in values]


def _build_mcq_compare(pool: TopicPool, rng, n: int) -> list[Question]:
    lo, hi = _number_range(pool.topic, pool.grade)
    out: list[Question] = []
    for _ in range(n):
        numbers = rng.sample(range(lo, hi + 1), 3)
        biggest = rng.random() < 0.6
        answer = max(numbers) if biggest else min(numbers)
        prompt = "सबसे बड़ी संख्या कौन सी है?" if biggest else "सबसे छोटी संख्या कौन सी है?"
        options = [str(x) for x in numbers]
        out.append(Question(
            qtype=TYPE_MCQ,
            instruction_hindi=INSTR_MCQ,
            body_hindi=prompt,
            options=options,
            answer=str(answer),
        ))
    return out


def _build_mcq_vocab(pool: TopicPool, rng, n: int) -> list[Question]:
    if len(pool.cards) < 3:
        return []
    out: list[Question] = []
    picks = rng.sample(pool.cards, min(n, len(pool.cards)))
    for card in picks:
        distractors = [c for c in pool.cards if c.id != card.id]
        options = [card.hindi_word] + [c.hindi_word for c in rng.sample(distractors, 2)]
        rng.shuffle(options)
        out.append(Question(
            qtype=TYPE_MCQ,
            instruction_hindi=INSTR_MCQ,
            body_hindi="चित्र देखो — यह क्या है?",
            visual=card.visual_emoji,
            options=options,
            answer=card.hindi_word,
            santali=card.santhali_ol_chiki if card.validation_status == content_service.AI_GENERATED else None,
        ))
    return out


def _build_mcq_shape(pool: TopicPool, rng, n: int) -> list[Question]:
    if len(pool.cards) < 3:
        return []
    out: list[Question] = []
    picks = rng.sample(pool.cards, min(n, len(pool.cards)))
    for card in picks:
        distractors = [c for c in pool.cards if c.id != card.id]
        options = [card.hindi_word] + [c.hindi_word for c in rng.sample(distractors, 2)]
        rng.shuffle(options)
        out.append(Question(
            qtype=TYPE_MCQ,
            instruction_hindi="चित्र देखो — यह कौन सा आकार है?",
            visual=card.visual_emoji,
            options=options,
            answer=card.hindi_word,
        ))
    return out


def _build_mcq_pattern(pool: TopicPool, rng, n: int) -> list[Question]:
    symbols = ["🍎", "🍌", "🔴", "🟢", "⭐", "📖"]
    out: list[Question] = []
    for _ in range(n):
        a, b = rng.sample(symbols, 2)
        pattern = [a, b, a, b, a]
        answer = b
        distractor = rng.choice([s for s in symbols if s not in {a, b}])
        options = [answer, distractor, a]
        rng.shuffle(options)
        out.append(Question(
            qtype=TYPE_MCQ,
            instruction_hindi="क्रम देखो — आगे क्या आएगा?",
            body_hindi="  ".join(pattern) + "  ____",
            options=options,
            answer=answer,
        ))
    return out


def _build_picture_word(pool: TopicPool, rng, n: int) -> list[Question]:
    if not pool.cards:
        return []
    out: list[Question] = []
    picks = rng.sample(pool.cards, min(n, len(pool.cards)))
    for card in picks:
        santali = card.santhali_ol_chiki if card.validation_status == content_service.AI_GENERATED else None
        out.append(Question(
            qtype=TYPE_PICTURE_WORD,
            instruction_hindi=INSTR_PICTURE,
            visual=card.visual_emoji,
            santali=santali,
            answer=card.hindi_word,
        ))
    return out


def _build_match(pool: TopicPool, rng, n: int, word_map: dict[str, str] | None) -> list[Question]:
    """Hindi <-> Santali matching pairs. Needs Santali (from cards or MT)."""
    pairs: list[tuple[str, str]] = []
    for card in pool.cards:
        if card.validation_status == content_service.AI_GENERATED and card.santhali_ol_chiki:
            pairs.append((card.hindi_word, card.santhali_ol_chiki))
    if word_map:
        for word, santali in word_map.items():
            if word not in {h for h, _ in pairs}:
                pairs.append((word, santali))
    if len(pairs) < 3:
        return []
    out: list[Question] = []
    remaining = pairs[:]
    rng.shuffle(remaining)
    while remaining and len(out) < n:
        take = min(5, len(remaining))
        chunk = remaining[:take]
        remaining = remaining[take:]
        santali_side = [s for _, s in chunk]
        rng.shuffle(santali_side)
        # answer: left index (1-based) -> right letter
        letters = "ABCDE"
        mapping = []
        for i, (hindi_w, santali_w) in enumerate(chunk):
            letter = letters[santali_side.index(santali_w)]
            mapping.append(f"{i + 1}-{letter}")
        out.append(Question(
            qtype=TYPE_MATCH,
            instruction_hindi=INSTR_MATCH,
            match_pairs=list(chunk),
            answer=", ".join(mapping),
        ))
    return out


def _build_vocab_practice(pool: TopicPool, rng, n: int, word_map: dict[str, str] | None) -> list[Question]:
    """One question = a small Hindi->Santali table (2-3 rows) + word bank."""
    pairs: list[tuple[str, str]] = []
    for card in pool.cards:
        if card.validation_status == content_service.AI_GENERATED and card.santhali_ol_chiki:
            pairs.append((card.hindi_word, card.santhali_ol_chiki))
    if word_map:
        for w, s in word_map.items():
            if w not in {h for h, _ in pairs}:
                pairs.append((w, s))
    if len(pairs) < 3:
        return []
    out: list[Question] = []
    remaining = pairs[:]
    rng.shuffle(remaining)
    while remaining and len(out) < n:
        take = min(3, len(remaining))
        chunk = remaining[:take]
        remaining = remaining[take:]
        bank = [s for _, s in chunk]
        rng.shuffle(bank)
        out.append(Question(
            qtype=TYPE_VOCAB_PRACTICE,
            instruction_hindi=INSTR_VOCAB,
            match_pairs=chunk,
            options=bank,  # word bank shown below the table
            answer=", ".join(s for _, s in chunk),
        ))
    return out


def _build_fill_sentence(pool: TopicPool, rng, n: int) -> list[Question]:
    """Blank one word of the lesson sentence + word bank of three."""
    if pool.lesson is None or len(pool.sentence_words) < 3:
        return []
    sentence = pool.lesson.hindi_text
    out: list[Question] = []
    candidates = [w for w in pool.sentence_words if len(w) >= 2]
    if not candidates:
        return []
    picks = [candidates[i % len(candidates)] for i in range(n)]
    for answer in picks:
        words = sentence.split(" ")
        target = next((w for w in words if answer in w), None)
        if target is None:
            continue
        blanked = " ".join("____" if w == target else w for w in words)
        distractors = [w for w in pool.sentence_words if w != answer and len(w) >= 2]
        if len(distractors) < 2:
            continue
        options_bank = [answer] + rng.sample(distractors, 2)
        rng.shuffle(options_bank)
        out.append(Question(
            qtype=TYPE_FILL_BLANK,
            instruction_hindi=INSTR_FILL_WORD,
            body_hindi=blanked,
            options=options_bank,  # word bank (also serves as write-in line)
            answer=answer,
        ))
    return out


def _plan_types(pool: TopicPool) -> list[str]:
    """Ordered type plan per topic; builders skip themselves when unusable."""
    topic = pool.topic
    numeracy = pool.lesson is not None and pool.lesson.subject == "numeracy"
    if topic in {"numbers-1-10", "counting"}:
        return [TYPE_COUNT, TYPE_FILL_BLANK, TYPE_MCQ, TYPE_MATCH, TYPE_PICTURE_WORD, TYPE_VOCAB_PRACTICE]
    if topic in {"numbers-11-20", "addition", "subtraction", "bigger-smaller"}:
        return [TYPE_FILL_BLANK, TYPE_MCQ]
    if topic == "shapes":
        return [TYPE_MCQ, TYPE_PICTURE_WORD, TYPE_COUNT, TYPE_MATCH, TYPE_VOCAB_PRACTICE]
    if topic == "patterns":
        return [TYPE_MCQ, TYPE_COUNT]
    if numeracy:
        return [TYPE_COUNT, TYPE_MCQ, TYPE_FILL_BLANK]
    # literacy
    if pool.cards:
        return [TYPE_PICTURE_WORD, TYPE_MCQ, TYPE_MATCH, TYPE_VOCAB_PRACTICE, TYPE_FILL_BLANK]
    return [TYPE_FILL_BLANK, TYPE_MCQ, TYPE_MATCH, TYPE_VOCAB_PRACTICE]


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def generate_worksheet(
    db: Session,
    grade: int,
    skill: str,
    topic: str,
    count: int,
    seed: int | None = None,
) -> dict:
    """
    Build one bilingual worksheet and write it to
    backend/generated_files/worksheets/ws_<hex>.html.

    Returns response metadata for the API layer. Hindi-only fallback: when
    the translation model is unavailable the worksheet still renders, with
    santali_available=False and no fabricated Santali text.
    """
    default_seed = int(hashlib.md5(f"{grade}:{skill}:{topic}".encode()).hexdigest()[:8], 16)
    rng = random.Random(seed if seed is not None else default_seed)

    pool = _build_pool(db, grade, skill, topic)
    santali_available = True
    if pool.cards:
        santali_available = _translate_missing_flashcards(db, pool.cards)

    instr: dict[str, str] = {}
    word_map: dict[str, str] | None = None
    if santali_available:
        # Instruction lines and sentence words are best-effort translations;
        # failing to fetch them must NOT hide the Santali that flashcards
        # already carry. Only a topic whose ONLY Santali source would be the
        # sentence words drops to Hindi-only mode.
        instr = _translated_instructions()
        words_needed = list(pool.sentence_words)
        word_map = _translate_words(words_needed) if words_needed else {}
        if word_map is None and not pool.cards:
            santali_available = False

    # ----- assemble questions -------------------------------------------------
    questions: list[Question] = []
    plan = _plan_types(pool)
    builder_rounds = 0
    while len(questions) < count and builder_rounds < 6:
        builder_rounds += 1
        for t in plan:
            if len(questions) >= count:
                break
            if t == TYPE_COUNT:
                got = _build_count(pool, rng, 2)
            elif t == TYPE_FILL_BLANK:
                got = _build_fill_sequence(pool, rng, 2) or _build_fill_sentence(pool, rng, 2)
            elif t == TYPE_MCQ:
                got = (
                    _build_mcq_arith(pool, rng, 2)
                    or _build_mcq_compare(pool, rng, 2)
                    or _build_mcq_shape(pool, rng, 2)
                    or _build_mcq_pattern(pool, rng, 2)
                    or _build_mcq_vocab(pool, rng, 2)
                )
            elif t == TYPE_PICTURE_WORD:
                got = _build_picture_word(pool, rng, 2)
            elif t == TYPE_MATCH:
                got = _build_match(pool, rng, 1, word_map)
            elif t == TYPE_VOCAB_PRACTICE:
                got = _build_vocab_practice(pool, rng, 1, word_map)
            else:
                got = []
            # avoid duplicate identical bodies in one sheet
            existing = {q.body_hindi for q in questions}
            for q in got:
                if len(questions) >= count:
                    break
                if q.body_hindi and q.body_hindi in existing:
                    continue
                existing.add(q.body_hindi)
                questions.append(q)

    questions = questions[:count]
    if not questions:
        # Should not happen with the seeded bank, but never 500 on a teacher.
        questions = [Question(
            qtype=TYPE_FILL_BLANK,
            instruction_hindi=INSTR_FILL_NUM,
            body_hindi="1 ,  2 ,  ____ ,  4",
            answer="3",
        )]

    # Attach the (once-per-sheet) Santali instruction lines
    for q in questions:
        q.instruction_santali = instr.get(q.instruction_hindi)

    types_included = sorted({q.qtype for q in questions})

    filename = f"ws_{uuid.uuid4().hex}.html"
    html_text = render_worksheet_html(
        grade=grade,
        skill=skill,
        pool=pool,
        questions=questions,
        types_included=types_included,
        santali_available=santali_available,
    )
    out_dir = settings.generated_files_path / "worksheets"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / filename
    out_path.write_text(html_text, encoding="utf-8")
    _cleanup_old_files(out_dir)

    logger.info(
        "Worksheet generated: %s (grade=%s skill=%s topic=%s questions=%d santali=%s)",
        filename, grade, skill, topic, len(questions), santali_available,
    )
    return {
        "filename": filename,
        "html_url": f"/api/worksheets/file/{filename}",
        "download_url": f"/api/worksheets/file/{filename}?download=1",
        "grade": grade,
        "skill": skill,
        "topic": topic,
        "topic_label": pool.label,
        "question_count": len(questions),
        "types_included": types_included,
        "santali_available": santali_available,
        "validation_notice": VALIDATION_NOTICE if santali_available else "",
        "nipun_note": NIPUN_NOTE,
        "offline": settings.OFFLINE_MODE,
    }


def _cleanup_old_files(out_dir: Path) -> None:
    try:
        files = sorted(out_dir.glob("ws_*.html"), key=lambda p: p.stat().st_mtime, reverse=True)
        for old in files[KEEP_FILES:]:
            old.unlink(missing_ok=True)
    except Exception:  # non-fatal housekeeping
        logger.debug("Worksheet cleanup skipped", exc_info=True)


# ---------------------------------------------------------------------------
# HTML rendering (self-contained; no external requests; browser prints PDF)
# ---------------------------------------------------------------------------

def _font_css() -> str:
    """@font-face rules with the Ol Chiki font embedded as base64 data URIs."""
    rules = []
    mime = "font/woff2"
    for key in ("olchiki", "latin"):
        path = _FONT_FILES[key]
        try:
            data = path.read_bytes()
        except OSError:
            continue  # font missing -> browser falls back to system fonts
        import base64

        b64 = base64.b64encode(data).decode("ascii")
        rules.append(
            "@font-face { font-family: 'Noto Sans Ol Chiki'; font-style: normal;"
            f" font-weight: 400; src: url(data:{mime};base64,{b64}) format('woff2'); }}"
        )
    return "\n".join(rules)


def _esc(text_value: str) -> str:
    return html.escape(str(text_value), quote=True)


def render_worksheet_html(
    grade: int,
    skill: str,
    pool: TopicPool,
    questions: list[Question],
    types_included: list[str],
    santali_available: bool,
) -> str:
    font_css = _font_css()
    skill_label = "Foundational Literacy" if skill == "literacy" else "Foundational Numeracy"

    q_blocks: list[str] = []
    match_letters = "ABCDE"
    for idx, q in enumerate(questions, start=1):
        label = TYPE_LABELS.get(q.qtype, "")
        head = (
            f'<div class="q-head"><span class="q-num">{idx}</span>'
            f'<span class="q-type">{_esc(label)}</span></div>'
        )
        instruction = f'<p class="q-instr">{_esc(q.instruction_hindi)}</p>'
        if q.instruction_santali:
            instruction += f'<p class="q-instr-santali ol-chiki">{_esc(q.instruction_santali)}</p>'
        visual = f'<div class="q-visual">{_esc(q.visual)}</div>' if q.visual else ""
        body = f'<p class="q-body">{_esc(q.body_hindi)}</p>' if q.body_hindi else ""
        santali_line = (
            f'<p class="q-santali ol-chiki">{_esc(q.santali)}</p>'
            if q.santali else ""
        )

        if q.qtype == TYPE_MATCH:
            left_rows = "".join(
                f'<tr><td class="m-num">{i + 1}</td><td class="m-word">{_esc(h)}</td></tr>'
                for i, (h, _s) in enumerate(q.match_pairs)
            )
            right_rows = "".join(
                f'<tr><td class="m-letter">{match_letters[i]}</td>'
                f'<td class="m-word ol-chiki">{_esc(s)}</td></tr>'
                for i, (_h, s) in enumerate(q.match_pairs)
            )
            table = (
                '<table class="match-table"><tr>'
                f'<td><table>{left_rows}</table></td>'
                '<td class="m-mid"></td>'
                f'<td><table>{right_rows}</table></td>'
                "</tr></table>"
            )
            answer_line = ""
            q_blocks.append(
                f'<div class="question">{head}{instruction}{table}</div>'
            )
            continue

        if q.qtype == TYPE_MCQ:
            opt_html = "".join(
                f'<span class="opt">({chr(97 + i)}) {_esc(o)}</span>'
                for i, o in enumerate(q.options)
            )
            q_blocks.append(
                f'<div class="question">{head}{instruction}{visual}{body}'
                f'<div class="opts">{opt_html}</div></div>'
            )
            continue

        if q.qtype == TYPE_VOCAB_PRACTICE:
            rows = "".join(
                f'<tr><td class="v-hindi">{_esc(h)}</td>'
                f'<td class="v-blank ol-chiki"></td></tr>'
                for h, _s in q.match_pairs
            )
            bank = " &nbsp;·&nbsp; ".join(
                f'<span class="ol-chiki">{_esc(s)}</span>' for s in q.options
            )
            table = (
                f'<table class="vocab-table">{rows}</table>'
                f'<p class="word-bank">शब्द-संग्रह / Word bank: {bank}</p>'
            )
            q_blocks.append(
                f'<div class="question">{head}{instruction}{table}</div>'
            )
            continue

        # Fill-blank / count-objects / picture-word: write-in answer line,
        # plus a word bank when the generator supplied candidate options.
        table = ""
        answer_line = '<p class="answer-line">उत्तर / Answer: <span class="blank"></span></p>'
        word_bank = ""
        if q.options:
            bank_items = " &nbsp;·&nbsp; ".join(_esc(o) for o in q.options)
            word_bank = f'<p class="word-bank">शब्द-संग्रह / Word bank: {bank_items}</p>'
        q_blocks.append(
            f'<div class="question">{head}{instruction}{visual}{body}{santali_line}{table}{word_bank}{answer_line}</div>'
        )

    santali_note = (
        "" if santali_available else
        '<p class="warn">Santali (Ol Chiki) text is not on this sheet because the local '
        "translation model is not ready yet. Generate translations first "
        "(see Model Status), then regenerate the worksheet.</p>"
    )
    notice = (
        f'<p class="foot-note">{_esc(VALIDATION_NOTICE)}</p>'
        if santali_available else ""
    )

    types_line = " · ".join(f"{t} — {_esc(TYPE_LABELS.get(t, ''))}" for t in types_included)

    return f"""<!DOCTYPE html>
<html lang="hi">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>RootVerse Bilingual Worksheet — {_esc(pool.label)}</title>
<style>
{font_css}
:root {{ --navy:#17293e; --green:#1e5c3d; --border:#c9c2b4; --soft:#e8f1ec; }}
* {{ box-sizing: border-box; }}
body {{ font-family: 'Noto Sans Devanagari','Nirmala UI',system-ui,sans-serif; color:#23303d;
       margin:0; background:#fff; font-size:15px; line-height:1.55; }}
.page {{ max-width: 800px; margin: 0 auto; padding: 28px 34px 40px; }}
.ol-chiki {{ font-family:'Noto Sans Ol Chiki','Noto Sans Devanagari',sans-serif; }}
.sheet-head {{ display:flex; justify-content:space-between; align-items:flex-start; gap:16px;
       border-bottom:3px solid var(--navy); padding-bottom:10px; }}
.sheet-head h1 {{ font-size:22px; margin:0 0 2px; color:var(--navy); }}
.sheet-head .sub {{ color:var(--green); font-weight:600; font-size:13px; margin:0; }}
.meta-chip {{ display:inline-block; border:1px solid var(--border); border-radius:999px;
       padding:2px 10px; font-size:12px; margin:0 4px 4px 0; background:var(--soft); }}
.student-line {{ display:flex; gap:24px; margin:14px 0 4px; font-size:14px; }}
.student-line span {{ flex:1; border-bottom:1.5px solid var(--border); padding-bottom:2px; }}
.nipun {{ font-size:11.5px; color:#63717f; margin:8px 0 0; }}
.types {{ font-size:11.5px; color:#63717f; margin:6px 0 0; }}
.question {{ border:1.5px solid var(--border); border-radius:10px; padding:12px 14px; margin:14px 0;
       page-break-inside: avoid; }}
.q-head {{ display:flex; align-items:center; gap:8px; margin-bottom:6px; }}
.q-num {{ background:var(--green); color:#fff; border-radius:50%; width:26px; height:26px;
       display:inline-flex; align-items:center; justify-content:center; font-weight:700; font-size:14px; }}
.q-type {{ font-size:11px; font-weight:700; letter-spacing:.4px; color:var(--green); text-transform:uppercase; }}
.q-instr {{ margin:2px 0 6px; font-weight:600; }}
.q-instr-santali {{ margin:-2px 0 6px; font-weight:600; color:var(--green); font-size:14px; }}
.q-body {{ font-size:17px; margin:4px 0; }}
.q-visual {{ font-size:30px; letter-spacing:6px; margin:6px 0; line-height:1.4; }}
.q-santali {{ background:var(--soft); border-radius:6px; padding:4px 10px; display:inline-block; margin:4px 0; }}
.opts {{ display:flex; flex-wrap:wrap; gap:10px 26px; margin-top:6px; font-size:16px; }}
.answer-line {{ margin:10px 0 0; }}
.blank {{ display:inline-block; min-width:180px; border-bottom:1.5px solid #23303d; }}
.match-table td {{ padding:8px 10px; }}
.m-num, .m-letter {{ font-weight:700; color:var(--navy); width:26px; }}
.m-word {{ font-size:17px; }}
.m-mid {{ width:70px; border-bottom:1.5px dotted var(--border); }}
.vocab-table {{ border-collapse:collapse; margin:6px 0; }}
.vocab-table td {{ border:1.5px solid var(--border); padding:9px 12px; font-size:17px; }}
.v-blank {{ min-width:220px; }}
.word-bank {{ font-size:14px; color:#41526b; background:#f5f3ec; border-radius:6px; padding:6px 10px; }}
.warn {{ background:#fdf1e2; border:1px solid #d97b21; color:#8a4d0d; border-radius:8px; padding:8px 12px; font-size:13px; }}
.answer-key {{ page-break-before: always; }}
.answer-key h2 {{ color:var(--navy); font-size:17px; }}
.answer-key ol {{ font-size:14px; }}
.foot {{ margin-top:22px; border-top:1.5px solid var(--border); padding-top:8px; font-size:11.5px; color:#63717f; }}
.foot-note {{ color:#b3540e; font-weight:700; font-size:12px; }}
.print-bar {{ position:sticky; top:0; background:#fff; padding:8px 0; text-align:right; }}
.print-bar button {{ background:var(--green); color:#fff; border:none; border-radius:8px;
       padding:10px 18px; font-size:14px; font-weight:600; cursor:pointer; }}
@media print {{
  .print-bar {{ display:none; }}
  .page {{ padding:0; max-width:none; }}
  body {{ font-size:13px; }}
  @page {{ margin: 14mm 12mm; }}
}}
</style>
</head>
<body>
<div class="page">
  <div class="print-bar"><button type="button" onclick="window.print()">🖨️ Print / Save as PDF</button></div>
  <div class="sheet-head">
    <div>
      <h1>RootVerse — बिलिंगुअल वर्कशीट</h1>
      <p class="sub">Bilingual Worksheet · Hindi + संताली (ᱚᱞ ᱪᱤᱠᱤ)</p>
    </div>
    <div style="text-align:right">
      <span class="meta-chip">कक्षा / Grade: {grade}</span>
      <span class="meta-chip">{_esc(skill_label)}</span>
      <span class="meta-chip">विषय / Topic: {_esc(pool.label)}</span>
    </div>
  </div>
  <div class="student-line"><span>नाम / Name:</span><span>दिनांक / Date:</span></div>
  <p class="nipun">{_esc(NIPUN_NOTE)}</p>
  <p class="types">Types: {types_line}</p>
  {santali_note}
  {''.join(q_blocks)}
  <div class="answer-key">
    <h2>उत्तर कुंजी (शिक्षक के लिए) / Answer Key</h2>
    <ol>
      {''.join(f'<li>{_esc(q.answer)}</li>' for q in questions)}
    </ol>
  </div>
  <div class="foot">
    <p>Generated offline by RootVerse (SIH 2026) — no cloud API was used.</p>
    {notice}
  </div>
</div>
</body>
</html>"""
