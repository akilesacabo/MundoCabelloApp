"""archive promotions instead of deleting them

Revision ID: 20260808_archive_promotions
Revises: 20260808_promotions
Create Date: 2026-08-08
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260808_archive_promotions"
down_revision: str | None = "20260808_promotions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("promocion") as batch:
        batch.add_column(
            sa.Column(
                "activo",
                sa.Boolean(),
                nullable=False,
                server_default=sa.true(),
            )
        )
        batch.create_index("promocion_activo_idx", ["activo"])


def downgrade() -> None:
    with op.batch_alter_table("promocion") as batch:
        batch.drop_index("promocion_activo_idx")
        batch.drop_column("activo")
