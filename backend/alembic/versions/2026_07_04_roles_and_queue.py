"""roles and public queue situation

Revision ID: 20260704_roles
Revises: 20260701_v2
Create Date: 2026-07-04
"""

import sqlalchemy as sa
from alembic import op


revision = "20260704_roles"
down_revision = "20260701_v2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "cliente",
        sa.Column("situacion", sa.String(16), server_default="normal", nullable=False),
    )
    op.create_index(op.f("cliente_situacion_idx"), "cliente", ["situacion"])


def downgrade() -> None:
    op.drop_index(op.f("cliente_situacion_idx"), table_name="cliente")
    op.drop_column("cliente", "situacion")
