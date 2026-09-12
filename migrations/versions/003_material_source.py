"""store the uploaded material object name

Revision ID: 003_material_source
Revises: 002_processing_fields
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "003_material_source"
down_revision: str | None = "002_processing_fields"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("units", sa.Column("material_object_name", sa.String(512)))


def downgrade() -> None:
    op.drop_column("units", "material_object_name")
