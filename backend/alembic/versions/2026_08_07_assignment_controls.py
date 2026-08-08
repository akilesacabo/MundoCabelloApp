"""assignment controls and client stylist preferences

Revision ID: 20260807_assignment_controls
Revises: 20260803_audit_actions
Create Date: 2026-08-07
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260807_assignment_controls"
down_revision: str | None = "20260803_audit_actions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "cliente",
        sa.Column("acepta_otro_estilista", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "turno_servicio", sa.Column("modificado_por_role", sa.String(20), nullable=True)
    )
    op.add_column(
        "turno_servicio",
        sa.Column("modificado_por_subject", sa.String(64), nullable=True),
    )
    op.add_column(
        "turno_servicio",
        sa.Column("modificado_por_nombre", sa.String(128), nullable=True),
    )
    op.add_column("turno_servicio", sa.Column("modificado_at", sa.DateTime(), nullable=True))
    op.create_table(
        "cliente_preseleccion",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "cliente_id",
            sa.Integer(),
            sa.ForeignKey("cliente.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "staff_numero",
            sa.Integer(),
            sa.ForeignKey("staff.numero", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.UniqueConstraint("cliente_id", "staff_numero"),
    )
    op.create_index(
        "ix_cliente_preseleccion_cliente_id", "cliente_preseleccion", ["cliente_id"]
    )
    op.create_index(
        "ix_cliente_preseleccion_staff_numero", "cliente_preseleccion", ["staff_numero"]
    )


def downgrade() -> None:
    op.drop_index("ix_cliente_preseleccion_staff_numero", table_name="cliente_preseleccion")
    op.drop_index("ix_cliente_preseleccion_cliente_id", table_name="cliente_preseleccion")
    op.drop_table("cliente_preseleccion")
    op.drop_column("turno_servicio", "modificado_at")
    op.drop_column("turno_servicio", "modificado_por_nombre")
    op.drop_column("turno_servicio", "modificado_por_subject")
    op.drop_column("turno_servicio", "modificado_por_role")
    op.drop_column("cliente", "acepta_otro_estilista")
