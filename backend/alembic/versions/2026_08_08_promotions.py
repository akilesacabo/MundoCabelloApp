"""add promotional bundles of existing services

Revision ID: 20260808_promotions
Revises: 20260808_head_spa_team
Create Date: 2026-08-08
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260808_promotions"
down_revision: str | None = "20260808_head_spa_team"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "promocion",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nombre", sa.String(length=128), nullable=False),
        sa.Column("precio_usd", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("nombre"),
    )
    op.create_index("promocion_nombre_idx", "promocion", ["nombre"])
    op.create_table(
        "promocion_servicio",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("promocion_id", sa.Integer(), nullable=False),
        sa.Column("service_catalog_id", sa.Integer(), nullable=False),
        sa.Column("precio_usd", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.ForeignKeyConstraint(["promocion_id"], ["promocion.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["service_catalog_id"], ["service_catalog.id"], ondelete="RESTRICT"
        ),
        sa.UniqueConstraint("promocion_id", "service_catalog_id"),
    )


def downgrade() -> None:
    op.drop_table("promocion_servicio")
    op.drop_index("promocion_nombre_idx", table_name="promocion")
    op.drop_table("promocion")
