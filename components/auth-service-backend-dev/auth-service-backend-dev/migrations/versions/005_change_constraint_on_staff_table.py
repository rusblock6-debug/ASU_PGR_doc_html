"""change personnel_number type to string and make patronymic nullable

Revision ID: 005
Revises: предыдущий_id_миграции
Create Date: 2026-03-02

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '005'
down_revision: Union[str, None] = '004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('staff', 'personnel_number',
                    type_=sa.String(),
                    existing_type=sa.Integer())

    op.alter_column('staff', 'patronymic',
                    existing_type=sa.String(),
                    nullable=True)


def downgrade() -> None:
    # Возвращаем обратно
    op.alter_column('staff', 'patronymic',
                    existing_type=sa.String(),
                    nullable=False)

    op.alter_column('staff', 'personnel_number',
                    type_=sa.Integer(),
                    existing_type=sa.String())
