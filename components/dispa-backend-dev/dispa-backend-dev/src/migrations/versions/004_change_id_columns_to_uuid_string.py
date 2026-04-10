"""Change id columns to UUID string in cycle_state_history and cycle_tag_history

Revision ID: 004
Revises: 003
Create Date: 2025-12-23 17:45:58.598662

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '004'
down_revision: Union[str, None] = '003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema"""
    # Изменяем id колонки в cycle_state_history с INTEGER на VARCHAR(50)
    op.alter_column(
        "cycle_state_history",
        "id",
        existing_type=sa.Integer(),
        type_=sa.String(length=50),
        existing_nullable=False,
        postgresql_using="gen_random_uuid()::text"  # Генерируем UUID для существующих записей
    )

    # Изменяем id колонки в cycle_tag_history с INTEGER на VARCHAR(50)
    op.alter_column(
        "cycle_tag_history",
        "id",
        existing_type=sa.Integer(),
        type_=sa.String(length=50),
        existing_nullable=False,
        postgresql_using="gen_random_uuid()::text"  # Генерируем UUID для существующих записей
    )


def downgrade() -> None:
    """Downgrade schema"""
    # Обратно изменяем id колонки в cycle_tag_history с VARCHAR(50) на INTEGER
    # Это может привести к потере данных, так как UUID нельзя конвертировать обратно в INTEGER
    op.alter_column(
        "cycle_tag_history",
        "id",
        existing_type=sa.String(length=50),
        type_=sa.Integer(),
        existing_nullable=False,
        postgresql_using="0"  # Устанавливаем 0 для всех записей (потеря данных)
    )

    # Обратно изменяем id колонки в cycle_state_history с VARCHAR(50) на INTEGER
    op.alter_column(
        "cycle_state_history",
        "id",
        existing_type=sa.String(length=50),
        type_=sa.Integer(),
        existing_nullable=False,
        postgresql_using="0"  # Устанавливаем 0 для всех записей (потеря данных)
    )

