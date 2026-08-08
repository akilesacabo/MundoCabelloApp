"""add Head Spa area and its responsible specialists

Revision ID: 20260808_head_spa_team
Revises: 20260807_assignment_controls
Create Date: 2026-08-08
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "20260808_head_spa_team"
down_revision: str | None = "20260807_assignment_controls"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

HEAD_SPA_SERVICES = "'HEAD SPA KUNDAL', 'HEAD SPA TOCTUS', 'HEAD SPA KOREAN'"
HEAD_SPA_STAFF = "47, 48, 49, 50"


def upgrade() -> None:
    op.execute(
        "INSERT INTO area (key, name, color) VALUES "
        "('head_spa', 'Head Spa', '#b9a5e5') ON CONFLICT DO NOTHING"
    )
    op.execute(
        "UPDATE service_catalog SET area_key = 'head_spa' "
        f"WHERE nombre IN ({HEAD_SPA_SERVICES})"
    )
    op.execute(
        "UPDATE turno_servicio SET area_key = 'head_spa' "
        f"WHERE nombre IN ({HEAD_SPA_SERVICES}) "
        "AND cliente_id IN (SELECT id FROM cliente WHERE activo = true)"
    )
    op.execute(
        "INSERT INTO staff_area (staff_numero, area_key) "
        f"SELECT numero, 'head_spa' FROM staff WHERE numero IN ({HEAD_SPA_STAFF}) "
        "ON CONFLICT DO NOTHING"
    )
    op.execute(
        "UPDATE staff SET nombre = 'Solmar Betania Gavidia Orellana', "
        "cedula = 'V-23.640.695', initials = 'SB' WHERE numero = 49"
    )


def downgrade() -> None:
    op.execute(
        "UPDATE service_catalog SET area_key = 'hidratacion' "
        f"WHERE nombre IN ({HEAD_SPA_SERVICES})"
    )
    op.execute(
        "UPDATE turno_servicio SET area_key = 'hidratacion' "
        f"WHERE nombre IN ({HEAD_SPA_SERVICES}) AND area_key = 'head_spa'"
    )
    op.execute("DELETE FROM staff_area WHERE area_key = 'head_spa'")
    op.execute("DELETE FROM area WHERE key = 'head_spa'")
