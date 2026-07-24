"""Perfiles permanentes, etiquetas y estados operativos claros.

Revision ID: 20260724_profiles
Revises: 20260704_roles
Create Date: 2026-07-24
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260724_profiles"
down_revision: str | None = "20260704_roles"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _normalize_cedula(value: str) -> str:
    compact = "".join(char for char in value.strip().upper() if char.isalnum())
    if compact[:1] in {"V", "E"}:
        return f"{compact[0]}-{compact[1:]}"
    return compact


def upgrade() -> None:
    op.create_table(
        "cliente_perfil",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("cedula", sa.String(length=20), nullable=False),
        sa.Column("nombre", sa.String(length=128), nullable=False),
        sa.Column("telefono", sa.String(length=25), nullable=False),
        sa.Column("direccion", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("cliente_perfil_pkey")),
    )
    op.create_index(
        op.f("cliente_perfil_cedula_idx"), "cliente_perfil", ["cedula"], unique=True
    )
    op.create_index(
        op.f("cliente_perfil_nombre_idx"), "cliente_perfil", ["nombre"], unique=False
    )

    with op.batch_alter_table("cliente") as batch:
        batch.add_column(sa.Column("perfil_id", sa.Integer(), nullable=True))
        batch.add_column(
            sa.Column(
                "activo",
                sa.Boolean(),
                server_default=sa.true(),
                nullable=False,
            )
        )
        batch.create_index(batch.f("cliente_perfil_id_idx"), ["perfil_id"], unique=False)
        batch.create_index(batch.f("cliente_activo_idx"), ["activo"], unique=False)
        batch.create_foreign_key(
            batch.f("cliente_perfil_id_fkey"),
            "cliente_perfil",
            ["perfil_id"],
            ["id"],
            ondelete="SET NULL",
        )

    op.create_table(
        "cliente_etiqueta",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("cliente_id", sa.Integer(), nullable=False),
        sa.Column("codigo", sa.String(length=16), nullable=False),
        sa.ForeignKeyConstraint(
            ["cliente_id"],
            ["cliente.id"],
            name=op.f("cliente_etiqueta_cliente_id_fkey"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("cliente_etiqueta_pkey")),
        sa.UniqueConstraint(
            "cliente_id", "codigo", name=op.f("cliente_etiqueta_cliente_id_key")
        ),
    )
    op.create_index(
        op.f("cliente_etiqueta_cliente_id_idx"),
        "cliente_etiqueta",
        ["cliente_id"],
        unique=False,
    )
    op.create_index(
        op.f("cliente_etiqueta_codigo_idx"),
        "cliente_etiqueta",
        ["codigo"],
        unique=False,
    )

    connection = op.get_bind()
    profiles: dict[str, int] = {}
    rows = connection.execute(
        sa.text(
            "SELECT id, cedula, nombre, telefono, direccion "
            "FROM cliente ORDER BY id DESC"
        )
    ).mappings()
    for row in rows:
        cedula = _normalize_cedula(row["cedula"])
        if cedula not in profiles:
            result = connection.execute(
                sa.text(
                    "INSERT INTO cliente_perfil "
                    "(cedula, nombre, telefono, direccion) "
                    "VALUES (:cedula, :nombre, :telefono, :direccion)"
                ),
                {
                    "cedula": cedula,
                    "nombre": row["nombre"],
                    "telefono": row["telefono"],
                    "direccion": row["direccion"],
                },
            )
            profiles[cedula] = int(result.lastrowid)
        connection.execute(
            sa.text(
                "UPDATE cliente SET perfil_id=:perfil_id, cedula=:cedula WHERE id=:id"
            ),
            {"perfil_id": profiles[cedula], "cedula": cedula, "id": row["id"]},
        )

    connection.execute(
        sa.text("UPDATE cliente SET situacion='presente' WHERE situacion='normal'")
    )
    connection.execute(
        sa.text(
            "UPDATE cliente SET activo=0 WHERE situacion='estafa' OR NOT EXISTS ("
            "SELECT 1 FROM turno_servicio "
            "WHERE turno_servicio.cliente_id=cliente.id "
            "AND turno_servicio.estado!='finalizado')"
        )
    )


def downgrade() -> None:
    connection = op.get_bind()
    connection.execute(
        sa.text("UPDATE cliente SET situacion='normal' WHERE situacion='presente'")
    )
    op.drop_index(op.f("cliente_etiqueta_codigo_idx"), table_name="cliente_etiqueta")
    op.drop_index(
        op.f("cliente_etiqueta_cliente_id_idx"), table_name="cliente_etiqueta"
    )
    op.drop_table("cliente_etiqueta")
    with op.batch_alter_table("cliente") as batch:
        batch.drop_constraint(batch.f("cliente_perfil_id_fkey"), type_="foreignkey")
        batch.drop_index(batch.f("cliente_activo_idx"))
        batch.drop_index(batch.f("cliente_perfil_id_idx"))
        batch.drop_column("activo")
        batch.drop_column("perfil_id")
    op.drop_index(op.f("cliente_perfil_nombre_idx"), table_name="cliente_perfil")
    op.drop_index(op.f("cliente_perfil_cedula_idx"), table_name="cliente_perfil")
    op.drop_table("cliente_perfil")
