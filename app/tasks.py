import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app._past_paper_repo import save_past_paper_questions
from app._question_extractor import _to_past_paper_question
from app.extractor import parse_past_paper
from app.minio_service import get_file_bytes_from_minio
from app.models import PastPaper, PastPaperContent, Unit


def process_past_paper(db: Session, paper: PastPaper) -> int:
    pdf_bytes = get_file_bytes_from_minio(paper.minio_object_name)
    parsed = parse_past_paper(pdf_bytes)
    questions = [_to_past_paper_question(question.question_text) for question in parsed.questions]
    content_record = db.scalar(
        select(PastPaperContent).where(PastPaperContent.past_paper_id == paper.id)
    )
    if content_record is None:
        db.add(PastPaperContent(past_paper_id=paper.id, content=parsed.content))
    else:
        content_record.content = parsed.content
    units = list(
        db.scalars(
            select(Unit).where(
                (Unit.material_object_name.is_(None))
                | Unit.source_material_id.is_not(None)
            )
        )
    )
    units = [
        unit
        for unit in units
        if unit.source_material_id is None
        or re.match(r"^\s*(?:unit|chapter|الوحدة|الفصل)\b", unit.name, re.IGNORECASE)
    ]
    return save_past_paper_questions(db, paper, questions, units)
