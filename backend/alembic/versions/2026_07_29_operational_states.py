"""Reposo, auditoría del check-in y área de maquillaje.

Revision ID: 20260729_operations
Revises: 20260724_profiles
Create Date: 2026-07-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260729_operations"
down_revision: str | None = "20260724_profiles"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("cliente") as batch:
        batch.add_column(sa.Column("registrado_por_role", sa.String(20), nullable=True))
        batch.add_column(
            sa.Column("registrado_por_subject", sa.String(64), nullable=True)
        )
        batch.add_column(
            sa.Column("registrado_por_nombre", sa.String(128), nullable=True)
        )

    connection = op.get_bind()
    connection.execute(
        sa.text(
            "INSERT INTO area (key, name, color) "
            "SELECT 'maquillaje', 'Maquillaje', '#b5739d' "
            "WHERE NOT EXISTS (SELECT 1 FROM area WHERE key='maquillaje')"
        )
    )
    connection.execute(
        sa.text("UPDATE area SET name='Cejas y depilación' WHERE key='cejas'")
    )
    connection.execute(
        sa.text(
            "UPDATE service_catalog SET area_key='maquillaje' "
            "WHERE upper(nombre) LIKE 'SERVICIO DE MAQUILLAJE%'"
        )
    )


def downgrade() -> None:
    connection = op.get_bind()
    connection.execute(
        sa.text(
            "UPDATE service_catalog SET area_key='peluqueria' "
            "WHERE area_key='maquillaje'"
        )
    )
    connection.execute(sa.text("UPDATE area SET name='Cejas' WHERE key='cejas'"))
    connection.execute(sa.text("DELETE FROM area WHERE key='maquillaje'"))
    with op.batch_alter_table("cliente") as batch:
        batch.drop_column("registrado_por_nombre")
        batch.drop_column("registrado_por_subject")
        batch.drop_column("registrado_por_role")
