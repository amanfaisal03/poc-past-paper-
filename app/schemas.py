from datetime import datetime

from pydantic import BaseModel, Field


class PastPaperResponse(BaseModel):
    id: int
    title: str
    minio_object_name: str
    processing_status: str
    error_message: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class UnitCreate(BaseModel):
    name: str = Field(min_length=1)
    description: str = ""


class UnitResponse(UnitCreate):
    id: int
    material_object_name: str | None = None
    content: str | None = None
    source_material_id: int | None = None
    position: int | None = None

    model_config = {"from_attributes": True}


class ContentResponse(BaseModel):
    id: int
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}


class QuestionResponse(BaseModel):
    id: int
    past_paper_id: int
    question_text: str
    question_type: str | None = None
    options: list[str] = Field(default_factory=list)
    marks: int | None = None
    section: str | None = None
    unit_id: int | None = None
    unit_title: str | None = None
    material_title: str | None = None
    classification_confidence: float | None = None
    classification_reason: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class QuestionUpdate(BaseModel):
    unit_id: int | None = None
    classification_confidence: float | None = Field(default=None, ge=0, le=1)
    classification_reason: str | None = None
