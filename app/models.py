from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.database import Base

class PastPaper(Base):
    __tablename__ = "past_papers"

    id = Column(Integer, primary_key=True)
    title = Column(String(255))
    minio_object_name = Column(String(512), unique=True)
    processing_status = Column(
        String(32), nullable=False, default="pending", server_default="pending"
    )
    error_message = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now() )

    questions = relationship("Question",back_populates="past_paper",cascade="all, delete-orphan")
    content = relationship(
        "PastPaperContent",
        back_populates="past_paper",
        uselist=False,
        cascade="all, delete-orphan",
    )


class MaterialContent(Base):
    __tablename__ = "material_contents"

    id = Column(Integer, primary_key=True)
    material_id = Column(ForeignKey("units.id"), unique=True, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    material = relationship("Unit", back_populates="content_record")


class PastPaperContent(Base):
    __tablename__ = "past_paper_contents"

    id = Column(Integer, primary_key=True)
    past_paper_id = Column(ForeignKey("past_papers.id"), unique=True, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    past_paper = relationship("PastPaper", back_populates="content")


class Unit(Base):
    __tablename__ = "units"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True)
    description = Column(Text, default="", server_default="")
    lesson_names = Column(JSONB, default=list, server_default="[]", nullable=False)
    material_object_name = Column(String(512), nullable=True)
    content = Column(Text, nullable=True)
    source_material_id = Column(ForeignKey("units.id"), nullable=True)
    position = Column(Integer, nullable=True)

    questions = relationship("Question", back_populates="unit")
    child_units = relationship("Unit", back_populates="source_material", foreign_keys=[source_material_id])
    source_material = relationship("Unit", remote_side=[id], back_populates="child_units", foreign_keys=[source_material_id])
    content_record = relationship(
        "MaterialContent",
        back_populates="material",
        uselist=False,
        cascade="all, delete-orphan",
    )


class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True)
    past_paper_id = Column(ForeignKey("past_papers.id"))
    question_text = Column(Text)
    question_type = Column(String(64), nullable=True)
    options = Column(JSONB, default=list, server_default="[]")
    marks = Column(Integer, nullable=True)
    section = Column(String(128), nullable=True)
    unit_id = Column(ForeignKey("units.id"), nullable=True)
    classification_confidence = Column(Float, nullable=True)
    classification_reason = Column(Text, nullable=True)
    lesson_title = Column(String(255), nullable=True)
    lesson_classification_confidence = Column(Float, nullable=True)
    lesson_classification_reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    past_paper = relationship("PastPaper", back_populates="questions")
    unit = relationship("Unit", back_populates="questions")

    @property
    def unit_title(self) -> str | None:
        return self.unit.name if self.unit else None

    @property
    def material_title(self) -> str | None:
        if self.unit is None:
            return None
        material = self.unit.source_material
        return material.name if material is not None else None
