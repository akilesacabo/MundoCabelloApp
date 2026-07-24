"""init v2: areas, service_catalog, staff (+staff_area), cliente (+turno_servicio,
servicio_cambio), historial.

Revision ID: 20260701_v2
Revises:
Create Date: 2026-07-01
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260701_v2"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "area",
        sa.Column("key", sa.String(32), nullable=False),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("color", sa.String(16), nullable=False),
        sa.PrimaryKeyConstraint("key", name=op.f("area_pkey")),
    )

    op.create_table(
        "service_catalog",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nombre", sa.String(128), nullable=False),
        sa.Column("area_key", sa.String(32), nullable=False),
        sa.Column("precio_usd", sa.Numeric(10, 2), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["area_key"], ["area.key"],
            name=op.f("service_catalog_area_key_fkey"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("service_catalog_pkey")),
    )
    op.create_index(op.f("service_catalog_nombre_idx"), "service_catalog", ["nombre"])
    op.create_index(op.f("service_catalog_area_key_idx"), "service_catalog", ["area_key"])

    op.create_table(
        "staff",
        sa.Column("numero", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("alias", sa.String(64), nullable=False),
        sa.Column("nombre", sa.String(128), nullable=False),
        sa.Column("cedula", sa.String(20), nullable=False),
        sa.Column("initials", sa.String(4), nullable=False),
        sa.Column("manual_status", sa.String(16), nullable=False),
        sa.Column("en_prueba", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("numero", name=op.f("staff_pkey")),
    )
    op.create_index(op.f("staff_manual_status_idx"), "staff", ["manual_status"])

    op.create_table(
        "staff_area",
        sa.Column("staff_numero", sa.Integer(), nullable=False),
        sa.Column("area_key", sa.String(32), nullable=False),
        sa.ForeignKeyConstraint(
            ["staff_numero"], ["staff.numero"],
            name=op.f("staff_area_staff_numero_fkey"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["area_key"], ["area.key"],
            name=op.f("staff_area_area_key_fkey"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "staff_numero", "area_key", name=op.f("staff_area_pkey")
        ),
    )

    op.create_table(
        "cliente",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("turno", sa.Integer(), nullable=False),
        sa.Column("cedula", sa.String(20), nullable=False),
        sa.Column("nombre", sa.String(128), nullable=False),
        sa.Column("telefono", sa.String(20), nullable=False),
        sa.Column("direccion", sa.String(255), nullable=False),
        sa.Column("observacion", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("cliente_pkey")),
    )
    op.create_index(op.f("cliente_turno_idx"), "cliente", ["turno"])
    op.create_index(op.f("cliente_cedula_idx"), "cliente", ["cedula"])
    op.create_index(op.f("cliente_created_at_idx"), "cliente", ["created_at"])

    op.create_table(
        "turno_servicio",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("cliente_id", sa.Integer(), nullable=False),
        sa.Column("area_key", sa.String(32), nullable=False),
        sa.Column("nombre", sa.String(128), nullable=False),
        sa.Column("precio_usd", sa.Numeric(10, 2), nullable=False),
        sa.Column("staff_numero", sa.Integer(), nullable=True),
        sa.Column("estado", sa.String(16), nullable=False),
        sa.ForeignKeyConstraint(
            ["cliente_id"], ["cliente.id"],
            name=op.f("turno_servicio_cliente_id_fkey"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["area_key"], ["area.key"],
            name=op.f("turno_servicio_area_key_fkey"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["staff_numero"], ["staff.numero"],
            name=op.f("turno_servicio_staff_numero_fkey"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("turno_servicio_pkey")),
    )
    op.create_index(op.f("turno_servicio_cliente_id_idx"), "turno_servicio", ["cliente_id"])
    op.create_index(op.f("turno_servicio_area_key_idx"), "turno_servicio", ["area_key"])
    op.create_index(op.f("turno_servicio_staff_numero_idx"), "turno_servicio", ["staff_numero"])
    op.create_index(op.f("turno_servicio_estado_idx"), "turno_servicio", ["estado"])

    op.create_table(
        "servicio_cambio",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("turno_servicio_id", sa.Integer(), nullable=False),
        sa.Column(
            "ts",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column("de_staff", sa.Integer(), nullable=True),
        sa.Column("a_staff", sa.Integer(), nullable=False),
        sa.Column("motivo", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["turno_servicio_id"], ["turno_servicio.id"],
            name=op.f("servicio_cambio_turno_servicio_id_fkey"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["de_staff"], ["staff.numero"],
            name=op.f("servicio_cambio_de_staff_fkey"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["a_staff"], ["staff.numero"],
            name=op.f("servicio_cambio_a_staff_fkey"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("servicio_cambio_pkey")),
    )
    op.create_index(
        op.f("servicio_cambio_turno_servicio_id_idx"),
        "servicio_cambio",
        ["turno_servicio_id"],
    )

    op.create_table(
        "historial",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "ts",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column("cliente_id", sa.Integer(), nullable=False),
        sa.Column("cliente_nombre", sa.String(128), nullable=False),
        sa.Column("cliente_cedula", sa.String(20), nullable=False),
        sa.Column("servicio_nombre", sa.String(128), nullable=False),
        sa.Column("area_key", sa.String(32), nullable=False),
        sa.Column("precio_usd", sa.Numeric(10, 2), nullable=False),
        sa.Column("staff_numero", sa.Integer(), nullable=True),
        sa.Column("staff_nombre", sa.String(128), nullable=False),
        sa.ForeignKeyConstraint(
            ["area_key"], ["area.key"],
            name=op.f("historial_area_key_fkey"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["staff_numero"], ["staff.numero"],
            name=op.f("historial_staff_numero_fkey"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("historial_pkey")),
    )
    op.create_index(op.f("historial_ts_idx"), "historial", ["ts"])
    op.create_index(op.f("historial_cliente_id_idx"), "historial", ["cliente_id"])
    op.create_index(op.f("historial_cliente_nombre_idx"), "historial", ["cliente_nombre"])
    op.create_index(op.f("historial_cliente_cedula_idx"), "historial", ["cliente_cedula"])
    op.create_index(op.f("historial_servicio_nombre_idx"), "historial", ["servicio_nombre"])
    op.create_index(op.f("historial_area_key_idx"), "historial", ["area_key"])
    op.create_index(op.f("historial_staff_numero_idx"), "historial", ["staff_numero"])


def downgrade() -> None:
    op.drop_table("historial")
    op.drop_table("servicio_cambio")
    op.drop_table("turno_servicio")
    op.drop_table("cliente")
    op.drop_table("staff_area")
    op.drop_table("staff")
    op.drop_table("service_catalog")
    op.drop_table("area")
