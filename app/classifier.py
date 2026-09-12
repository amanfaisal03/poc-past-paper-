import json
import re
import unicodedata

from openai import OpenAI

from app._question_extractor import PastPaperQuestion
from app.database import settings
from app.models import Unit


def match_question_to_unit(
    question: PastPaperQuestion, units: list[Unit]
) -> tuple[Unit | None, float | None, str | None]:
    if settings.openai_api_key:
        return _match_question_with_llm(question, units)
    return _match_question_by_keywords(question, units)


def _match_question_with_llm(
    question: PastPaperQuestion, units: list[Unit]
) -> tuple[Unit | None, float | None, str | None]:
    catalog = [
        {"id": unit.id, "title": unit.name, "description": unit.description or ""}
        for unit in units
    ]
    response = OpenAI(api_key=settings.openai_api_key).chat.completions.create(
        model=settings.openai_model,
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": (
                    "Classify an Arabic or English exam question into the best "
                    "academic unit. Return JSON with unit_id, confidence from 0 "
                    "to 1, and a short reason. Use null when no unit fits."
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
    raw = response.choices[0].message.content
    if not raw:
        raise RuntimeError("LLM classifier returned an empty response")
    try:
        result = json.loads(raw)
        unit_id = result.get("unit_id")
        confidence = float(result.get("confidence", 0))
        reason = str(result.get("reason", "LLM classification"))
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise RuntimeError("LLM classifier returned invalid JSON") from exc

    selected = next((unit for unit in units if unit.id == unit_id), None)
    if selected is None:
        return None, None, reason
    return selected, max(0.0, min(1.0, confidence)), reason


def _match_question_by_keywords(
    question: PastPaperQuestion, units: list[Unit]
) -> tuple[Unit | None, float | None, str | None]:
    question_words = _normalized_words(question.question_text)
    best_unit: Unit | None = None
    best_score = 0
    for unit in units:
        score = len(
            question_words
            & _normalized_words(f"{unit.name} {unit.description}")
        )
        if score > best_score:
            best_unit, best_score = unit, score
    if best_unit is None:
        return None, None, "No matching unit keywords were found (LLM not configured)"
    return best_unit, min(0.95, 0.5 + best_score * 0.1), f"Matched {best_score} unit keyword(s)"


def _normalized_words(text: str) -> set[str]:
    normalized = unicodedata.normalize("NFKC", text).lower()
    normalized = "".join(
        character for character in normalized
        if unicodedata.category(character) != "Mn"
    )
    words = set(re.findall(r"[^\W_]+", normalized, flags=re.UNICODE))
    return {word[:-1] if word.endswith("s") and len(word) > 3 else word for word in words}
