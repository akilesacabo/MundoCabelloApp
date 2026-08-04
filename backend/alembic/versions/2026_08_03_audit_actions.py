"""audit administrative actions

Revision ID: 20260803_audit_actions
Revises: 20260729_operations
Create Date: 2026-08-03
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260803_audit_actions"
down_revision: str | None = "20260729_operations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "cliente",
        sa.Column("actualizado_por_role", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "cliente",
        sa.Column("actualizado_por_subject", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "cliente",
        sa.Column("actualizado_por_nombre", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "turno_servicio",
        sa.Column("asignado_por_role", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "turno_servicio",
        sa.Column("asignado_por_subject", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "turno_servicio",
        sa.Column("asignado_por_nombre", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "servicio_cambio",
        sa.Column("cambiado_por_role", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "servicio_cambio",
        sa.Column("cambiado_por_subject", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "servicio_cambio",
        sa.Column("cambiado_por_nombre", sa.String(length=128), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("servicio_cambio", "cambiado_por_nombre")
    op.drop_column("servicio_cambio", "cambiado_por_subject")
    op.drop_column("servicio_cambio", "cambiado_por_role")
    op.drop_column("turno_servicio", "asignado_por_nombre")
    op.drop_column("turno_servicio", "asignado_por_subject")
    op.drop_column("turno_servicio", "asignado_por_role")
    op.drop_column("cliente", "actualizado_por_nombre")
    op.drop_column("cliente", "actualizado_por_subject")
    op.drop_column("cliente", "actualizado_por_role")
