"""store lesson classification results"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "007_lesson_classification"
down_revision: str | None = "006_content_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("questions", sa.Column("lesson_title", sa.String(255), nullable=True))
    op.add_column(
        "questions",
        sa.Column("lesson_classification_confidence", sa.Float(), nullable=True),
    )
    op.add_column(
        "questions",
        sa.Column("lesson_classification_reason", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("questions", "lesson_classification_reason")
    op.drop_column("questions", "lesson_classification_confidence")
    op.drop_column("questions", "lesson_title")
