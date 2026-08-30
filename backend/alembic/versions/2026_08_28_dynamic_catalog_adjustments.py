"""dynamic areas, catalog soft delete and service adjustments

Revision ID: 20260828_catalog_adjustments
Revises: 20260808_archive_promotions
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260828_catalog_adjustments"
down_revision: str | None = "20260808_archive_promotions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("area") as batch:
        batch.add_column(
            sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true())
        )
        batch.create_index("area_activo_idx", ["activo"])

    with op.batch_alter_table("service_catalog") as batch:
        batch.add_column(
            sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true())
        )
        batch.create_index("service_catalog_activo_idx", ["activo"])

    with op.batch_alter_table("staff") as batch:
        batch.add_column(
            sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true())
        )
        batch.create_index("staff_activo_idx", ["activo"])

    with op.batch_alter_table("turno_servicio") as batch:
        batch.add_column(
            sa.Column(
                "origen", sa.String(16), nullable=False, server_default="legacy"
            )
        )
        batch.add_column(sa.Column("promocion_id", sa.Integer(), nullable=True))
        batch.add_column(
            sa.Column(
                "ajuste_usd", sa.Numeric(10, 2), nullable=False, server_default="0"
            )
        )
        batch.add_column(sa.Column("ajuste_por_role", sa.String(20), nullable=True))
        batch.add_column(sa.Column("ajuste_por_subject", sa.String(64), nullable=True))
        batch.add_column(sa.Column("ajuste_por_nombre", sa.String(128), nullable=True))
        batch.add_column(sa.Column("ajuste_at", sa.DateTime(), nullable=True))
        batch.create_foreign_key(
            "turno_servicio_promocion_id_fkey",
            "promocion",
            ["promocion_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch.create_index("turno_servicio_origen_idx", ["origen"])
        batch.create_index("turno_servicio_promocion_id_idx", ["promocion_id"])

    with op.batch_alter_table("historial") as batch:
        batch.add_column(
            sa.Column(
                "precio_base_usd",
                sa.Numeric(10, 2),
                nullable=False,
                server_default="0",
            )
        )
        batch.add_column(
            sa.Column(
                "ajuste_usd", sa.Numeric(10, 2), nullable=False, server_default="0"
            )
        )
    op.execute("UPDATE historial SET precio_base_usd = precio_usd")


def downgrade() -> None:
    with op.batch_alter_table("historial") as batch:
        batch.drop_column("ajuste_usd")
        batch.drop_column("precio_base_usd")

    with op.batch_alter_table("turno_servicio") as batch:
        batch.drop_index("turno_servicio_promocion_id_idx")
        batch.drop_index("turno_servicio_origen_idx")
        batch.drop_constraint("turno_servicio_promocion_id_fkey", type_="foreignkey")
        batch.drop_column("ajuste_at")
        batch.drop_column("ajuste_por_nombre")
        batch.drop_column("ajuste_por_subject")
        batch.drop_column("ajuste_por_role")
        batch.drop_column("ajuste_usd")
        batch.drop_column("promocion_id")
        batch.drop_column("origen")

    with op.batch_alter_table("staff") as batch:
        batch.drop_index("staff_activo_idx")
        batch.drop_column("activo")

    with op.batch_alter_table("service_catalog") as batch:
        batch.drop_index("service_catalog_activo_idx")
        batch.drop_column("activo")

    with op.batch_alter_table("area") as batch:
        batch.drop_index("area_activo_idx")
        batch.drop_column("activo")
