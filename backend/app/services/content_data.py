"""
Phase 5 FLN content pack — Hindi SOURCE content only.

HONESTY RULES (datasets/README.md, unchanged):
  - NO Santali text is written by hand anywhere in this file.
  - Every Santali field starts as the placeholder REQUIRES_LANGUAGE_VALIDATION
    and is filled ONLY by the existing offline IndicTrans2 translation
    service (Phase 2). Translated content is marked AI_GENERATED and is
    always shown with the notice
    "AI-generated — Requires native-speaker validation".
  - Hindi lesson content is simple, deterministic classroom language written
    by the development team; it contains no factual claims that could be
    "fake educational facts".

NIPUN BHARAT WORDING (required):
  We never claim official NIPUN Bharat certification. The exact wording used
  across UI and worksheets is NIPUN_NOTE below.
"""

from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Shared wording (single source of truth for API + frontend + worksheets)
# ---------------------------------------------------------------------------

VALIDATION_NOTICE = "AI-generated — Requires native-speaker validation"
NIPUN_NOTE = (
    "Designed around foundational literacy and numeracy skills relevant to "
    "NIPUN Bharat goals."
)
PLACEHOLDER = "REQUIRES_LANGUAGE_VALIDATION"


@dataclass
class LessonSpec:
    """One FLN lesson (Hindi source text; Santali filled by the MT service)."""

    title_hindi: str
    title_english: str
    category: str
    subject: str          # literacy | numeracy (== "skill group")
    skill: str            # specific FLN skill, e.g. "Counting"
    class_level: int      # 1 | 2 | 3
    hindi_text: str
    learning_objective: str
    activity_instruction: str


@dataclass
class FlashcardSpec:
    """One visual flashcard (emoji + optional bundled SVG key; local assets only)."""

    topic: str
    hindi_word: str
    english_word: str
    visual_emoji: str
    image_key: str | None = None


# ---------------------------------------------------------------------------
# 1. FLN lesson bank — 18 lessons (10 literacy + 8 numeracy)
# ---------------------------------------------------------------------------

LESSON_BANK: list[LessonSpec] = [
    # ---------------- Foundational Literacy ----------------
    LessonSpec(
        title_hindi="अभिवादन और कक्षा-संवाद",
        title_english="Greetings & Classroom Talk",
        category="greetings",
        subject="literacy",
        skill="Speaking and listening",
        class_level=1,
        hindi_text="नमस्ते! आप कैसे हैं? मैं ठीक हूँ, धन्यवाद।",
        learning_objective="Student greets the teacher and answers simple classroom questions.",
        activity_instruction="शिक्षक नमस्ते कहें; विद्यार्थी मिलकर अभिवादन का अभ्यास करें।",
    ),
    LessonSpec(
        title_hindi="वर्णमाला परिचय",
        title_english="Introduction to the Alphabet",
        category="alphabet",
        subject="literacy",
        skill="Letter-sound recognition",
        class_level=1,
        hindi_text="आज हम कुछ पहले अक्षर पहचानेंगे।",
        learning_objective="Student recognizes and says the first letters of the Hindi alphabet.",
        activity_instruction="शिक्षक अक्षर दिखाएँ; विद्यार्थी मिलकर बोलें और हवा में लिखें।",
    ),
    LessonSpec(
        title_hindi="सरल शब्द",
        title_english="Simple Words",
        category="simple-words",
        subject="literacy",
        skill="Word reading",
        class_level=1,
        hindi_text="हम आसान शब्द पढ़ेंगे: कमल, घर, मछली।",
        learning_objective="Student reads and says simple everyday Hindi words.",
        activity_instruction="शब्द कार्ड दिखाओ; विद्यार्थी मिलकर पढ़ें और दोहराएँ।",
    ),
    LessonSpec(
        title_hindi="कक्षा की वस्तुएँ",
        title_english="Classroom Objects",
        category="classroom-objects",
        subject="literacy",
        skill="Vocabulary",
        class_level=1,
        hindi_text="किताब, कलम और बोर्ड कक्षा की वस्तुएँ हैं।",
        learning_objective="Student names common objects found in the classroom.",
        activity_instruction="कक्षा की वस्तुएँ देखो और उनके नाम बोलो।",
    ),
    LessonSpec(
        title_hindi="जानवर",
        title_english="Animals",
        category="animals",
        subject="literacy",
        skill="Vocabulary",
        class_level=1,
        hindi_text="बिल्ली, कुत्ता और गाय जानवर हैं।",
        learning_objective="Student names common animals and the sounds they make.",
        activity_instruction="जानवरों के चित्र दिखाओ; विद्यार्थी नाम और आवाज़ बताएँ।",
    ),
    LessonSpec(
        title_hindi="फल",
        title_english="Fruits",
        category="fruits",
        subject="literacy",
        skill="Vocabulary",
        class_level=1,
        hindi_text="सेब, केला और आम स्वादिष्ट फल हैं।",
        learning_objective="Student names common fruits and says their colours.",
        activity_instruction="फलों के चित्र दिखाओ और रंग के साथ नाम बोलो।",
    ),
    LessonSpec(
        title_hindi="रंग पहचानो",
        title_english="Recognize Colors",
        category="colours",
        subject="literacy",
        skill="Vocabulary",
        class_level=1,
        hindi_text="आज हम रंगों के नाम सीखेंगे।",
        learning_objective="Student names common colours found in the classroom.",
        activity_instruction="कक्षा की चीज़ों के रंग बताओ और मिलकर दोहराओ।",
    ),
    LessonSpec(
        title_hindi="शरीर के अंग",
        title_english="Body Parts",
        category="body-parts",
        subject="literacy",
        skill="Vocabulary",
        class_level=1,
        hindi_text="आँख से देखते हैं और कान से सुनते हैं।",
        learning_objective="Student names basic body parts and what they do.",
        activity_instruction="शिक्षक अंग बताएँ; विद्यार्थी छूकर नाम बोलें।",
    ),
    LessonSpec(
        title_hindi="परिवार",
        title_english="Family",
        category="family",
        subject="literacy",
        skill="Vocabulary",
        class_level=1,
        hindi_text="माता, पिता और भाई-बहन मिलकर परिवार बनाते हैं।",
        learning_objective="Student names the members of a family.",
        activity_instruction="अपने परिवार के सदस्यों के बारे में बोलो और नाम गिनो।",
    ),
    LessonSpec(
        title_hindi="छोटे वाक्य",
        title_english="Simple Sentence Comprehension",
        category="sentences",
        subject="literacy",
        skill="Reading comprehension",
        class_level=2,
        hindi_text="मैं स्कूल जाता हूँ। मैं किताब पढ़ता हूँ।",
        learning_objective="Student listens to and understands short everyday sentences.",
        activity_instruction="वाक्य सुनो, दोहराओ और सही चित्र चुनो।",
    ),
    # ---------------- Foundational Numeracy ----------------
    LessonSpec(
        title_hindi="गिनती: एक से दस",
        title_english="Numbers: One to Ten",
        category="numbers-1-10",
        subject="numeracy",
        skill="Counting",
        class_level=1,
        hindi_text="आज हम एक से दस तक गिनती सीखेंगे।",
        learning_objective="Student counts aloud from 1 to 10 and shows numbers on fingers.",
        activity_instruction="सभी विद्यार्थी मिलकर एक से दस तक गिनें और उंगलियों से संख्या दिखाएँ।",
    ),
    LessonSpec(
        title_hindi="गिनती: ग्यारह से बीस",
        title_english="Numbers 11 to 20",
        category="numbers-11-20",
        subject="numeracy",
        skill="Counting",
        class_level=2,
        hindi_text="आज हम ग्यारह से बीस तक गिनती सीखेंगे।",
        learning_objective="Student counts aloud from 11 to 20.",
        activity_instruction="ग्यारह से बीस तक मिलकर गिनो और उंगलियों से दिखाओ।",
    ),
    LessonSpec(
        title_hindi="वस्तुओं की गिनती",
        title_english="Counting Objects",
        category="counting",
        subject="numeracy",
        skill="Counting objects",
        class_level=1,
        hindi_text="कक्षा की वस्तुएँ गिनो और सही संख्या बताओ।",
        learning_objective="Student counts real objects up to ten and says the total.",
        activity_instruction="कक्षा में रखी वस्तुएँ गिनो और संख्या लिखो।",
    ),
    LessonSpec(
        title_hindi="बड़ा और छोटा",
        title_english="Bigger and Smaller",
        category="bigger-smaller",
        subject="numeracy",
        skill="Comparison",
        class_level=1,
        hindi_text="दो वस्तुओं में से बड़ी वस्तु पहचानो।",
        learning_objective="Student compares two objects/numbers and identifies the bigger one.",
        activity_instruction="दो पेंसिल दिखाओ; विद्यार्थी बड़ी पेंसिल चुनें।",
    ),
    LessonSpec(
        title_hindi="जोड़: एक से पाँच",
        title_english="Addition Basics",
        category="addition",
        subject="numeracy",
        skill="Addition",
        class_level=2,
        hindi_text="दो संख्याओं को जोड़कर जोड़ निकालो।",
        learning_objective="Student adds two single-digit numbers using objects or fingers.",
        activity_instruction="उंगलियों से जोड़ो: दो उंगलियाँ और तीन उंगलियाँ = कितनी?",
    ),
    LessonSpec(
        title_hindi="घटाव: दस तक",
        title_english="Subtraction Basics",
        category="subtraction",
        subject="numeracy",
        skill="Subtraction",
        class_level=2,
        hindi_text="बड़ी संख्या में से छोटी संख्या घटाओ।",
        learning_objective="Student subtracts a smaller number from a number up to ten.",
        activity_instruction="पाँच चीज़ें रखो, दो हटाओ; बची चीज़ें गिनो।",
    ),
    LessonSpec(
        title_hindi="आकार: गोल, त्रिकोण, चौकोर",
        title_english="Shapes: Circle, Triangle, Square",
        category="shapes",
        subject="numeracy",
        skill="Shape recognition",
        class_level=1,
        hindi_text="आज हम आकार पहचानेंगे।",
        learning_objective="Student names circle, triangle and square.",
        activity_instruction="कक्षा में गोल, त्रिकोण और चौकोर चीज़ें ढूँढो और नाम बताओ।",
    ),
    LessonSpec(
        title_hindi="क्रम और पैटर्न",
        title_english="Patterns",
        category="patterns",
        subject="numeracy",
        skill="Pattern recognition",
        class_level=2,
        hindi_text="आगे क्या आएगा? क्रम पूरा करो।",
        learning_objective="Student completes simple repeating patterns.",
        activity_instruction="क्रम बनाओ: लाल, नीला, लाल, नीला… आगे क्या आएगा?",
    ),
]

# Legacy Phase 1-2 seed lessons (rows created before Phase 5 had no category).
# We UPGRADE those rows in place (never delete user data) by matching their
# English title; they then belong to the Phase 5 categories below.
LEGACY_LESSON_CATEGORIES: dict[str, tuple[str, str]] = {
    # title_english -> (category, skill)
    "Numbers: One to Ten": ("numbers-1-10", "Counting"),
    "Introduction to the Alphabet": ("alphabet", "Letter-sound recognition"),
    "Shapes: Circle, Triangle, Square": ("shapes", "Shape recognition"),
    "Recognize Colors": ("colours", "Vocabulary"),
}

# ---------------------------------------------------------------------------
# 2. Classroom phrase pack — additions over the Phase 1-2 seed.
# The Phase 1-2 seed already contains: अपनी किताब खोलो / ध्यान से सुनो /
# अपना नाम लिखो / एक से दस तक गिनो / सब लोग खड़े हो जाओ / मेरे बाद दोहराओ /
# कक्षा में शांत रहो / बहुत अच्छा किया.
# ---------------------------------------------------------------------------

PHRASE_PACK_ADDITIONS: list[dict[str, str]] = [
    {"hindi": "बैठ जाओ।", "english": "Sit down.", "category": "instruction"},
    {"hindi": "खड़े हो जाओ।", "english": "Stand up.", "category": "instruction"},
    {"hindi": "फिर से बोलो।", "english": "Say it again.", "category": "instruction"},
    {"hindi": "चित्र को देखो।", "english": "Look at the picture.", "category": "instruction"},
    {"hindi": "शब्द पढ़ो।", "english": "Read the word.", "category": "instruction"},
]

# ---------------------------------------------------------------------------
# 3. Flashcards — 6 topics, 40 cards. Visuals: emoji + bundled SVG keys
#    (frontend/public/flashcards/<image_key>.svg). No external images.
# ---------------------------------------------------------------------------

FLASHCARD_TOPICS: list[dict[str, str]] = [
    {"topic": "numbers", "label_hindi": "संख्याएँ", "label_english": "Numbers"},
    {"topic": "colours", "label_hindi": "रंग", "label_english": "Colours"},
    {"topic": "animals", "label_hindi": "जानवर", "label_english": "Animals"},
    {"topic": "fruits", "label_hindi": "फल", "label_english": "Fruits"},
    {"topic": "classroom-objects", "label_hindi": "कक्षा की वस्तुएँ", "label_english": "Classroom objects"},
    {"topic": "shapes", "label_hindi": "आकार", "label_english": "Shapes"},
]

FLASHCARD_PACK: list[FlashcardSpec] = [
    # Numbers 1-10 (10 cards)
    FlashcardSpec("numbers", "एक", "One", "1️⃣"),
    FlashcardSpec("numbers", "दो", "Two", "2️⃣"),
    FlashcardSpec("numbers", "तीन", "Three", "3️⃣"),
    FlashcardSpec("numbers", "चार", "Four", "4️⃣"),
    FlashcardSpec("numbers", "पाँच", "Five", "5️⃣"),
    FlashcardSpec("numbers", "छह", "Six", "6️⃣"),
    FlashcardSpec("numbers", "सात", "Seven", "7️⃣"),
    FlashcardSpec("numbers", "आठ", "Eight", "8️⃣"),
    FlashcardSpec("numbers", "नौ", "Nine", "9️⃣"),
    FlashcardSpec("numbers", "दस", "Ten", "🔟"),
    # Colours (6 cards)
    FlashcardSpec("colours", "लाल", "Red", "🔴"),
    FlashcardSpec("colours", "हरा", "Green", "🟢"),
    FlashcardSpec("colours", "पीला", "Yellow", "🟡"),
    FlashcardSpec("colours", "नीला", "Blue", "🔵"),
    FlashcardSpec("colours", "काला", "Black", "⚫"),
    FlashcardSpec("colours", "सफ़ेद", "White", "⚪"),
    # Animals (6 cards)
    FlashcardSpec("animals", "बिल्ली", "Cat", "🐱", "cat"),
    FlashcardSpec("animals", "कुत्ता", "Dog", "🐶", "dog"),
    FlashcardSpec("animals", "गाय", "Cow", "🐄"),
    FlashcardSpec("animals", "बकरी", "Goat", "🐐"),
    FlashcardSpec("animals", "हाथी", "Elephant", "🐘"),
    FlashcardSpec("animals", "मोर", "Peacock", "🦚"),
    # Fruits (6 cards)
    FlashcardSpec("fruits", "सेब", "Apple", "🍎", "apple"),
    FlashcardSpec("fruits", "केला", "Banana", "🍌"),
    FlashcardSpec("fruits", "आम", "Mango", "🥭"),
    FlashcardSpec("fruits", "संतरा", "Orange", "🍊"),
    FlashcardSpec("fruits", "अंगूर", "Grapes", "🍇"),
    FlashcardSpec("fruits", "नारियल", "Coconut", "🥥"),
    # Classroom objects (6 cards)
    FlashcardSpec("classroom-objects", "किताब", "Book", "📖", "book"),
    FlashcardSpec("classroom-objects", "कलम", "Pen", "🖊️"),
    FlashcardSpec("classroom-objects", "पेंसिल", "Pencil", "✏️"),
    FlashcardSpec("classroom-objects", "कुर्सी", "Chair", "🪑"),
    FlashcardSpec("classroom-objects", "बस्ता", "School bag", "🎒"),
    FlashcardSpec("classroom-objects", "बोर्ड", "Board", "📋"),
    # Shapes (6 cards)
    FlashcardSpec("shapes", "गोल", "Circle", "⭕", "circle"),
    FlashcardSpec("shapes", "त्रिकोण", "Triangle", "🔺", "triangle"),
    FlashcardSpec("shapes", "चौकोर", "Square", "🟩"),
    FlashcardSpec("shapes", "सितारा", "Star", "⭐"),
    FlashcardSpec("shapes", "हीरा", "Diamond", "🔶"),
    FlashcardSpec("shapes", "दिल", "Heart", "❤️"),
]

# Extra bundled SVGs (sun, tree) ship in frontend/public/flashcards/ for
# teachers/future topics; they are not referenced by the initial card pack.

# ---------------------------------------------------------------------------
# 4. Worksheet topic catalogue (label + which lesson category feeds it)
# ---------------------------------------------------------------------------

WORKSHEET_TOPICS: list[dict[str, str]] = [
    {"skill": "literacy", "topic": "greetings", "label_hindi": "अभिवादन", "label_english": "Greetings"},
    {"skill": "literacy", "topic": "alphabet", "label_hindi": "वर्णमाला", "label_english": "Alphabet"},
    {"skill": "literacy", "topic": "simple-words", "label_hindi": "सरल शब्द", "label_english": "Simple words"},
    {"skill": "literacy", "topic": "classroom-objects", "label_hindi": "कक्षा की वस्तुएँ", "label_english": "Classroom objects"},
    {"skill": "literacy", "topic": "animals", "label_hindi": "जानवर", "label_english": "Animals"},
    {"skill": "literacy", "topic": "fruits", "label_hindi": "फल", "label_english": "Fruits"},
    {"skill": "literacy", "topic": "colours", "label_hindi": "रंग", "label_english": "Colours"},
    {"skill": "literacy", "topic": "body-parts", "label_hindi": "शरीर के अंग", "label_english": "Body parts"},
    {"skill": "literacy", "topic": "family", "label_hindi": "परिवार", "label_english": "Family"},
    {"skill": "literacy", "topic": "sentences", "label_hindi": "छोटे वाक्य", "label_english": "Sentences"},
    {"skill": "numeracy", "topic": "numbers-1-10", "label_hindi": "संख्या १-१०", "label_english": "Numbers 1-10"},
    {"skill": "numeracy", "topic": "numbers-11-20", "label_hindi": "संख्या ११-२०", "label_english": "Numbers 11-20"},
    {"skill": "numeracy", "topic": "counting", "label_hindi": "गिनती", "label_english": "Counting objects"},
    {"skill": "numeracy", "topic": "bigger-smaller", "label_hindi": "बड़ा-छोटा", "label_english": "Bigger / smaller"},
    {"skill": "numeracy", "topic": "addition", "label_hindi": "जोड़", "label_english": "Addition"},
    {"skill": "numeracy", "topic": "subtraction", "label_hindi": "घटाव", "label_english": "Subtraction"},
    {"skill": "numeracy", "topic": "shapes", "label_hindi": "आकार", "label_english": "Shapes"},
    {"skill": "numeracy", "topic": "patterns", "label_hindi": "पैटर्न", "label_english": "Patterns"},
]


def lesson_specs_for_category(category: str) -> list[LessonSpec]:
    return [s for s in LESSON_BANK if s.category == category]


def worksheet_topic_label(topic: str) -> str:
    for row in WORKSHEET_TOPICS:
        if row["topic"] == topic:
            return f"{row['label_hindi']} / {row['label_english']}"
    return topic
