"""link TOC units to their source material

Revision ID: 004_material_units
Revises: 003_material_source
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "004_material_units"
down_revision: str | None = "003_material_source"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("units", sa.Column("source_material_id", sa.Integer(), nullable=True))
    op.add_column("units", sa.Column("position", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_units_source_material_id",
        "units",
        "units",
        ["source_material_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_units_source_material_id", "units", type_="foreignkey")
    op.drop_column("units", "position")
    op.drop_column("units", "source_material_id")
