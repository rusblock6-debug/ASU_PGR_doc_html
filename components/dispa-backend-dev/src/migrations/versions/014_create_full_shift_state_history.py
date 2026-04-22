"""Create full_shift_state_history table

Revision ID: 014
Revises: 013
Create Date: 2026-02-05

Создает таблицу full_shift_state_history для хранения обобщенных статусов смен.
Таблица используется периодической таской для агрегации данных из cycle_state_history.
"""
from typing import Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "014"
down_revision: Union[str, None] = "013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Создать таблицу full_shift_state_history.
    
    Поля:
    - id: str (PK) - UUID идентификатор
    - vehicle_id: int - ID транспортного средства
    - shift_num: int - номер смены
    - shift_date: str - дата смены (формат: YYYY-MM-DD)
    - state: str - system_name статуса (work/idle/no_data)
    - timestamp: datetime - время начала смены
    - source: str - источник данных
    - is_processed: bool - флаг обработки/пересчета (True по умолчанию)
    """
    
    op.create_table(
        "full_shift_state_history",
        sa.Column("id", sa.String(50), primary_key=True),
        sa.Column("vehicle_id", sa.Integer(), nullable=False, index=True),
        sa.Column("shift_num", sa.Integer(), nullable=False),
        sa.Column("shift_date", sa.String(50), nullable=False),
        sa.Column("state", sa.String(50), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("source", sa.String(20), nullable=False, server_default="system"),
        sa.Column("is_processed", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # Составной индекс для быстрого поиска по vehicle_id + shift_date + shift_num
    op.create_index(
        "ix_full_shift_state_history_vehicle_shift",
        "full_shift_state_history",
        ["vehicle_id", "shift_date", "shift_num"],
        unique=True
    )
    
    # Индекс для поиска необработанных записей
    op.create_index(
        "ix_full_shift_state_history_is_processed",
        "full_shift_state_history",
        ["is_processed"],
        postgresql_where=sa.text("is_processed = false")
    )


def downgrade() -> None:
    """
    Удалить таблицу full_shift_state_history.
    """
    op.drop_index("ix_full_shift_state_history_is_processed", table_name="full_shift_state_history")
    op.drop_index("ix_full_shift_state_history_vehicle_shift", table_name="full_shift_state_history")
    op.drop_table("full_shift_state_history")
