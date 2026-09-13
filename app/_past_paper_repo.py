from sqlalchemy.orm import Session

from app._question_extractor import PastPaperQuestion
from app.classifier import classify_question
from app.models import PastPaper, Question, Unit


def save_past_paper_questions(
    db: Session,
    paper: PastPaper,
    questions: list[PastPaperQuestion],
    units: list[Unit],
) -> int:
    db.query(Question).filter(Question.past_paper_id == paper.id).delete()

    for question in questions:
        classification = classify_question(question, units)
        db.add(
            Question(
                past_paper_id=paper.id,
                question_text=question.question_text,
                question_type=question.question_type,
                options=question.options,
                marks=question.marks,
                section=question.section,
                unit_id=classification.unit.id if classification.unit else None,
                classification_confidence=classification.unit_confidence,
                classification_reason=classification.unit_reason,
                lesson_title=classification.lesson_title,
                lesson_classification_confidence=classification.lesson_confidence,
                lesson_classification_reason=classification.lesson_reason,
            )
        )

    return len(questions)
