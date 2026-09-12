"""store processed material text

Revision ID: 005_material_content
Revises: 004_material_units
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "005_material_content"
down_revision: str | None = "004_material_units"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("units", sa.Column("content", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("units", "content")
