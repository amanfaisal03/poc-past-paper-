import re

from pydantic import BaseModel, Field


_OPTION_MARKER = re.compile(r"(?:^|\s)[*•\-]?\s*([أبجدA-Da-d])\s*[\):\-]\s*")



class PastPaperQuestion(BaseModel):
    question_text: str
    question_type: str | None = None
    options: list[str] = Field(default_factory=list)
    marks: int | None = None
    section: str | None = None


def _to_past_paper_question(text: str) -> PastPaperQuestion:
    matches = list(_OPTION_MARKER.finditer(text))
    if len(matches) < 2:
        return PastPaperQuestion(question_text=text)

    question_text = text[: matches[0].start()].strip()
    options: list[str] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        option = text[match.end() : end].strip(" \n-*")
        if option:
            options.append(option)

    return PastPaperQuestion(
        question_text=question_text or text,
        question_type="multiple_choice",
        options=options,
    )
