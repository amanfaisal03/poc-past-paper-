from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.material_extractor import extract_material
from app.minio_service import get_file_bytes_from_minio, upload_file_to_minio
from app.models import (
    MaterialContent,
    PastPaper,
    PastPaperContent,
    Question,
    Unit,
)
from app.tasks import process_past_paper as process_past_paper_task
from app.schemas import (
    PastPaperResponse,
    QuestionResponse,
    QuestionUpdate,
    UnitCreate,
    UnitResponse,
    ContentResponse,
)

router = APIRouter()
DatabaseSession = Annotated[Session, Depends(get_db)]


@router.post(
    "/past-papers",
    response_model=PastPaperResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_past_paper(
    db: DatabaseSession,
    title: Annotated[str, Form(min_length=1)],
    file: Annotated[UploadFile, File()],
) -> PastPaper:
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    if not file.filename:
        raise HTTPException(status_code=400, detail="A PDF filename is required")

    file_content = await file.read()
    if not file_content:
        raise HTTPException(status_code=400, detail="The PDF file is empty")

    object_name = upload_file_to_minio(
        file_content=file_content,
        file_name=file.filename,
        content_type="application/pdf",
    )
    paper = PastPaper(
        title=title,
        minio_object_name=object_name,
    )
    db.add(paper)
    db.commit()
    db.refresh(paper)
    return paper


@router.get("/past-papers", response_model=list[PastPaperResponse])
def list_past_papers(db: DatabaseSession) -> list[PastPaper]:
    return list(db.scalars(select(PastPaper).order_by(PastPaper.created_at.desc())))


@router.get("/past-papers/{past_paper_id}", response_model=PastPaperResponse)
def get_past_paper(past_paper_id: int, db: DatabaseSession) -> PastPaper:
    paper = db.get(PastPaper, past_paper_id)
    if paper is None:
        raise HTTPException(status_code=404, detail="Past paper not found")
    return paper


@router.post("/past-papers/{past_paper_id}/process")
def process_past_paper(past_paper_id: int, db: DatabaseSession) -> dict[str, str | int]:
    paper = get_past_paper(past_paper_id, db)
    paper.processing_status = "processing"
    paper.error_message = None
    db.commit()

    try:
        questions_extracted = process_past_paper_task(db, paper)
        paper.processing_status = "done"
        db.commit()
    except (OSError, RuntimeError, ValueError) as exc:
        db.rollback()
        paper = get_past_paper(past_paper_id, db)
        paper.processing_status = "failed"
        paper.error_message = str(exc)
        db.commit()
        status_code = (
            503
            if str(exc) == "LLAMA_CLOUD_API_KEY is not configured"
            else 502
        )
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc

    return {
        "id": paper.id,
        "status": paper.processing_status,
        "questions_extracted": questions_extracted,
    }


@router.post("/units",response_model=UnitResponse, status_code=status.HTTP_201_CREATED)
def create_unit(unit: UnitCreate, db: DatabaseSession) -> Unit:
    existing = db.scalar(select(Unit).where(Unit.name == unit.name))
    if existing is not None:
        raise HTTPException(status_code=409, detail="A unit with this name already exists")

    db_unit = Unit(**unit.model_dump())
    db.add(db_unit)
    db.commit()
    db.refresh(db_unit)
    return db_unit


@router.post(
    "/materials",
    response_model=UnitResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_material(
    db: DatabaseSession,
    title: Annotated[str, Form(min_length=1)],
    file: Annotated[UploadFile, File()],
) -> Unit:
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Materials must be PDF files")

    if not file.filename:
        raise HTTPException(status_code=400, detail="A material filename is required")

    existing = db.scalar(select(Unit).where(Unit.name == title))
    if existing is not None:
        raise HTTPException(status_code=409, detail="A material with this title already exists")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="The material file is empty")

    object_name = upload_file_to_minio(
        file_content=content,
        file_name=file.filename,
        content_type="application/pdf",
    )
    material = Unit(name=title, material_object_name=object_name)
    db.add(material)
    db.commit()
    db.refresh(material)
    return material


@router.post(
    "/materials/{material_id}/split",
    response_model=list[UnitResponse],
)
def split_material_into_units(material_id: int, db: DatabaseSession) -> list[Unit]:
    material = db.get(Unit, material_id)
    if material is None or material.material_object_name is None:
        raise HTTPException(status_code=404, detail="Material not found")

    try:
        pdf_bytes = get_file_bytes_from_minio(material.material_object_name)
        extracted = extract_material(pdf_bytes)
        material.content = extracted.content
        content_record = db.scalar(
            select(MaterialContent).where(MaterialContent.material_id == material.id)
        )
        if content_record is None:
            db.add(
                MaterialContent(material_id=material.id, content=extracted.content)
            )
        else:
            content_record.content = extracted.content
        old_units = list(
            db.scalars(select(Unit).where(Unit.source_material_id == material.id))
        )
        old_unit_ids = [unit.id for unit in old_units]
        if old_unit_ids:
            db.query(Question).filter(Question.unit_id.in_(old_unit_ids)).update(
                {Question.unit_id: None}, synchronize_session=False
            )
            for old_unit in old_units:
                db.delete(old_unit)
            db.flush()
        units: list[Unit] = []
        for position, name in enumerate(extracted.unit_names, start=1):
            unit = db.scalar(select(Unit).where(Unit.name == name))
            if unit is None:
                unit = Unit(
                    name=name,
                    source_material_id=material.id,
                    position=position,
                    content=extracted.unit_names,
                )
                db.add(unit)
            elif unit.source_material_id == material.id:
                unit.position = position
                unit.content = extracted.unit_names
            units.append(unit)
        db.commit()
        for unit in units:
            db.refresh(unit)
        return units
    except (OSError, RuntimeError, ValueError) as exc:
        db.rollback()
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get(
    "/materials/{material_id}",
    response_model=UnitResponse,
)
def get_material(material_id: int, db: DatabaseSession) -> Unit:
    material = db.get(Unit, material_id)
    if material is None or material.material_object_name is None:
        raise HTTPException(status_code=404, detail="Material not found")
    return material


@router.get(
    "/materials/{material_id}/content",
    response_model=ContentResponse,
)
def get_material_content(material_id: int, db: DatabaseSession) -> MaterialContent:
    material = db.get(Unit, material_id)
    if material is None or material.material_object_name is None:
        raise HTTPException(status_code=404, detail="Material not found")
    content = db.scalar(
        select(MaterialContent).where(MaterialContent.material_id == material_id)
    )
    if content is None:
        raise HTTPException(status_code=404, detail="Material has not been processed")
    return content


@router.get(
    "/past-papers/{past_paper_id}/content",
    response_model=ContentResponse,
)
def get_past_paper_content(
    past_paper_id: int, db: DatabaseSession
) -> PastPaperContent:
    paper = get_past_paper(past_paper_id, db)
    content = db.scalar(
        select(PastPaperContent).where(PastPaperContent.past_paper_id == paper.id)
    )
    if content is None:
        raise HTTPException(status_code=404, detail="Past paper has not been processed")
    return content


@router.get(
    "/materials/{material_id}/units",
    response_model=list[UnitResponse],
)
def list_material_units(material_id: int, db: DatabaseSession) -> list[Unit]:
    material = db.get(Unit, material_id)
    if material is None or material.material_object_name is None:
        raise HTTPException(status_code=404, detail="Material not found")
    return list(
        db.scalars(
            select(Unit)
            .where(Unit.source_material_id == material_id)
            .order_by(Unit.position, Unit.id)
        )
    )


@router.get("/units/{unit_id}/questions", response_model=list[QuestionResponse])
def get_unit_questions(unit_id: int, db: DatabaseSession) -> list[Question]:
    if db.get(Unit, unit_id) is None:
        raise HTTPException(status_code=404, detail="Unit not found")
    return list(
        db.scalars(select(Question).where(Question.unit_id == unit_id))
    )


@router.get(
    "/past-papers/{past_paper_id}/questions",
    response_model=list[QuestionResponse],
)
def get_past_paper_questions(
    past_paper_id: int, db: DatabaseSession
) -> list[Question]:
    get_past_paper(past_paper_id, db)
    return list(
        db.scalars(select(Question).where(Question.past_paper_id == past_paper_id))
    )


@router.patch("/questions/{question_id}", response_model=QuestionResponse)
def update_question(
    question_id: int, update: QuestionUpdate, db: DatabaseSession
) -> Question:
    question = db.get(Question, question_id)
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found")

    values = update.model_dump(exclude_unset=True)
    if "unit_id" in values and values["unit_id"] is not None:
        if db.get(Unit, values["unit_id"]) is None:
            raise HTTPException(status_code=404, detail="Unit not found")

    for field, value in values.items():
        setattr(question, field, value)
    db.commit()
    db.refresh(question)
    return question
