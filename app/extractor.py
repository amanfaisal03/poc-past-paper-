import logging
import re
from dataclasses import dataclass

from app.database import settings


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ExtractedQuestion:
    question_text: str
    question_type: str | None = None
    options: list[str] | None = None
    marks: int | None = None
    section: str | None = None


@dataclass(frozen=True)
class ParsedPastPaper:
    content: str
    questions: list[ExtractedQuestion]


_QUESTION_MARKER = re.compile(r"(?<!\d)(\d{1,2})\s*[\.\):\-]\s+")


def parse_past_paper(pdf_bytes: bytes) -> ParsedPastPaper:
    if not settings.llama_cloud_api_key:
        raise RuntimeError("LLAMA_CLOUD_API_KEY is not configured")

    from llama_cloud import LlamaCloud

    client = LlamaCloud(api_key=settings.llama_cloud_api_key)

    result = client.parsing.parse(
        tier=settings.llama_parse_tier,
        version="latest",
        upload_file=("past-paper.pdf", pdf_bytes, "application/pdf"),
        expand=["markdown_full"],
    )

    text = result.markdown_full or result.text_full or ""

    client.close()

    if not text:
        raise RuntimeError("Llama Cloud returned no text for the PDF")

    questions = _split_questions(text)

    return ParsedPastPaper(
        content=text,
        questions=questions,
    )


def _split_questions(text: str) -> list[ExtractedQuestion]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    questions = []
    current = []

    for line in lines:
        if _QUESTION_MARKER.match(line):
            if current:
                questions.append(
                    ExtractedQuestion(question_text=" ".join(current))
                )
            current = [line]
        else:
            current.append(line)

    if current:
        questions.append(
            ExtractedQuestion(question_text=" ".join(current))
        )

    return questions
