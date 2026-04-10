"""Create shift_route_templates table

Revision ID: 020
Revises: 019
Create Date: 2026-03-05

Создает таблицу shift_route_templates для хранения шаблонов маршрутов
для конкретной смены (shift_date, shift_num) с парами мест (place_a_id, place_b_id),
которые должны отображаться в сводке маршрутов даже при отсутствии наряд-заданий.
"""

from typing import Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "020"
down_revision: Union[str, None] = "019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Создать таблицу shift_route_templates."""
    op.create_table(
        "shift_route_templates",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("shift_date", sa.String(length=50), nullable=False),
        sa.Column("shift_num", sa.Integer(), nullable=False),
        sa.Column("place_a_id", sa.Integer(), nullable=False),
        sa.Column("place_b_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint(
            "shift_date",
            "shift_num",
            "place_a_id",
            "place_b_id",
            name="uq_shift_route_templates_shift_place",
        ),
    )

    # Индексы по полям смены для быстрого поиска
    op.create_index(
        "ix_shift_route_templates_shift_date",
        "shift_route_templates",
        ["shift_date"],
    )
    op.create_index(
        "ix_shift_route_templates_shift_num",
        "shift_route_templates",
        ["shift_num"],
    )


def downgrade() -> None:
    """Удалить таблицу shift_route_templates."""
    op.drop_index(
        "ix_shift_route_templates_shift_num",
        table_name="shift_route_templates",
    )
    op.drop_index(
        "ix_shift_route_templates_shift_date",
        table_name="shift_route_templates",
    )
    op.drop_table("shift_route_templates")

