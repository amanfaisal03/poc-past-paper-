"""store parsed material and past-paper content separately

Revision ID: 006_content_tables
Revises: 005_material_content
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "006_content_tables"
down_revision: str | None = "005_material_content"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "material_contents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("material_id", sa.Integer(), nullable=False, unique=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["material_id"], ["units.id"]),
    )
    op.create_table(
        "past_paper_contents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("past_paper_id", sa.Integer(), nullable=False, unique=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["past_paper_id"], ["past_papers.id"]),
    )


def downgrade() -> None:
    op.drop_table("past_paper_contents")
    op.drop_table("material_contents")
