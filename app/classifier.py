import json
import re
import unicodedata
from dataclasses import dataclass

from openai import OpenAI

from app._question_extractor import PastPaperQuestion
from app.database import settings
from app.models import Unit


@dataclass(frozen=True)
class ClassificationResult:
    unit: Unit | None
    unit_confidence: float | None
    unit_reason: str | None
    lesson_title: str | None
    lesson_confidence: float | None
    lesson_reason: str | None


def classify_question(
    question: PastPaperQuestion,
    units: list[Unit],
) -> ClassificationResult:
    lesson_titles = [
        lesson
        for unit in units
        for lesson in (unit.lesson_names or [])
    ]

    if settings.openai_api_key:
        return classify_with_llm(question, units)

    return classify_with_keywords(question, units, lesson_titles)


def classify_with_llm(
    question: PastPaperQuestion,
    units: list[Unit],
) -> ClassificationResult:
    client = OpenAI(api_key=settings.openai_api_key)

    catalog = [
        {
            "id": unit.id,
            "title": unit.name,
            "description": unit.description or "",
            "lessons": unit.lesson_names or [],
        }
        for unit in units
    ]

    response = client.chat.completions.create(
        model=settings.openai_model,
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": (
                    "Classify the exam question into the best unit and lesson. "
                    "Return JSON with: unit_id, lesson_title, "
                    "unit_confidence, lesson_confidence, "
                    "unit_reason, lesson_reason."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "question": question.question_text,
                        "options": question.options,
                        "units": catalog,
                    },
                    ensure_ascii=False,
                ),
            },
        ],
    )

    result = json.loads(response.choices[0].message.content)

    unit = next(
        (unit for unit in units if str(unit.id) == str(result["unit_id"])),
        None,
    )

    return ClassificationResult(
        unit=unit,
        unit_confidence=result.get("unit_confidence"),
        unit_reason=result.get("unit_reason"),
        lesson_title=result.get("lesson_title"),
        lesson_confidence=result.get("lesson_confidence"),
        lesson_reason=result.get("lesson_reason"),
    )


def classify_with_keywords(
    question: PastPaperQuestion,
    units: list[Unit],
    lesson_titles: list[str],
) -> ClassificationResult:
    words = normalize_words(question.question_text)

    best_unit = None
    best_unit_score = 0

    for unit in units:
        text = f"{unit.name} {unit.description or ''}"
        score = len(words & normalize_words(text))

        if score > best_unit_score:
            best_unit = unit
            best_unit_score = score

    best_lesson = None
    best_lesson_score = 0

    for lesson in lesson_titles:
        score = len(words & normalize_words(lesson))

        if score > best_lesson_score:
            best_lesson = lesson
            best_lesson_score = score

    return ClassificationResult(
        unit=best_unit,
        unit_confidence=confidence(best_unit_score),
        unit_reason=f"Matched {best_unit_score} keyword(s)",
        lesson_title=best_lesson,
        lesson_confidence=confidence(best_lesson_score),
        lesson_reason=f"Matched {best_lesson_score} keyword(s)",
    )


def confidence(score: int) -> float | None:
    if score == 0:
        return None

    return min(0.95, 0.5 + score * 0.1)


def normalize_words(text: str) -> set[str]:
    text = unicodedata.normalize("NFKC", text).lower()

    text = "".join(
        char
        for char in text
        if unicodedata.category(char) != "Mn"
    )

    return set(re.findall(r"[^\W_]+", text, re.UNICODE))