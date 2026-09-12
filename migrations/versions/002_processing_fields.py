"""add processing and question detail fields

Revision ID: 002_processing_fields
Revises: 001
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "002_processing_fields"
down_revision: str | None = "001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "past_papers",
        sa.Column(
            "processing_status",
            sa.String(length=32),
            server_default="pending",
            nullable=False,
        ),
    )
    op.add_column("past_papers", sa.Column("error_message", sa.Text(), nullable=True))
    op.add_column("questions", sa.Column("marks", sa.Integer(), nullable=True))
    op.add_column("questions", sa.Column("section", sa.String(length=128), nullable=True))


def downgrade() -> None:
    op.drop_column("questions", "section")
    op.drop_column("questions", "marks")
    op.drop_column("past_papers", "error_message")
    op.drop_column("past_papers", "processing_status")
