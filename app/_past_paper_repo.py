from sqlalchemy.orm import Session

from app._question_extractor import PastPaperQuestion
from app.classifier import match_question_to_unit
from app.models import PastPaper, Question, Unit


def save_past_paper_questions(
    db: Session,
    paper: PastPaper,
    questions: list[PastPaperQuestion],
    units: list[Unit],
) -> int:
    db.query(Question).filter(Question.past_paper_id == paper.id).delete()

    for question in questions:
        unit, confidence, reason = match_question_to_unit(question, units)
        db.add(
            Question(
                past_paper_id=paper.id,
                question_text=question.question_text,
                question_type=question.question_type,
                options=question.options,
                marks=question.marks,
                section=question.section,
                unit_id=unit.id if unit else None,
                classification_confidence=confidence,
                classification_reason=reason,
            )
        )

    return len(questions)
