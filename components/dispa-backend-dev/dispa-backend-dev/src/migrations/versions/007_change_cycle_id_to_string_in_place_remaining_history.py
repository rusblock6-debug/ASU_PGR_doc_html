"""
Изменение типа cycle_id в place_remaining_history с UUID на String(50).

Revision ID: 007
Revises: 006
Create Date: 2025-01-XX
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from loguru import logger


# revision identifiers, used by Alembic.
revision: str = '007'
down_revision: Union[str, None] = '006'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Изменение типа cycle_id с UUID на String(50)."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    # Проверяем, существует ли таблица
    tables = inspector.get_table_names()
    if "place_remaining_history" not in tables:
        logger.warning("Migration 007: place_remaining_history table does not exist, skipping")
        return
    
    # Проверяем текущий тип колонки
    cols = {c["name"]: c["type"] for c in inspector.get_columns("place_remaining_history")}
    
    if "cycle_id" not in cols:
        logger.warning("Migration 007: cycle_id column does not exist, skipping")
        return
    
    # Проверяем, является ли текущий тип UUID
    col_type = cols["cycle_id"]
    is_uuid = isinstance(col_type, postgresql.UUID) or col_type.__class__.__name__ == "UUID"
    
    if is_uuid:
        # Временно удаляем индекс, если он существует
        existing_indexes = {i["name"] for i in inspector.get_indexes("place_remaining_history")}
        if "ix_place_remaining_history_cycle_id" in existing_indexes:
            op.drop_index(
                "ix_place_remaining_history_cycle_id",
                table_name="place_remaining_history"
            )
        
        # Изменяем тип колонки с UUID на String(50)
        # Конвертируем UUID в строку, используя ::text
        op.alter_column(
            "place_remaining_history",
            "cycle_id",
            existing_type=postgresql.UUID(as_uuid=False),
            type_=sa.String(length=50),
            existing_nullable=True,
            postgresql_using="cycle_id::text",
        )
        
        # Восстанавливаем индекс
        op.create_index(
            "ix_place_remaining_history_cycle_id",
            "place_remaining_history",
            ["cycle_id"],
        )
        
        logger.info("Migration 007: Changed cycle_id type from UUID to String(50)")
    else:
        logger.info("Migration 007: cycle_id is already String type, skipping")


def downgrade() -> None:
    """Обратное изменение типа cycle_id с String(50) на UUID."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    tables = inspector.get_table_names()
    if "place_remaining_history" not in tables:
        logger.warning("Migration 007 downgrade: place_remaining_history table does not exist, skipping")
        return
    
    cols = {c["name"]: c["type"] for c in inspector.get_columns("place_remaining_history")}
    
    if "cycle_id" not in cols:
        logger.warning("Migration 007 downgrade: cycle_id column does not exist, skipping")
        return
    
    col_type = cols["cycle_id"]
    is_string = isinstance(col_type, sa.String) or col_type.__class__.__name__ == "VARCHAR"
    
    if is_string:
        # Временно удаляем индекс
        existing_indexes = {i["name"] for i in inspector.get_indexes("place_remaining_history")}
        if "ix_place_remaining_history_cycle_id" in existing_indexes:
            op.drop_index(
                "ix_place_remaining_history_cycle_id",
                table_name="place_remaining_history"
            )
        
        # Изменяем тип колонки обратно с String(50) на UUID
        # Пытаемся конвертировать строку в UUID, если не получается - устанавливаем NULL
        op.alter_column(
            "place_remaining_history",
            "cycle_id",
            existing_type=sa.String(length=50),
            type_=postgresql.UUID(as_uuid=False),
            existing_nullable=True,
            postgresql_using="NULLIF(cycle_id, '')::uuid",
        )
        
        # Восстанавливаем индекс
        op.create_index(
            "ix_place_remaining_history_cycle_id",
            "place_remaining_history",
            ["cycle_id"],
        )
        
        logger.info("Migration 007 downgrade: Changed cycle_id type from String(50) to UUID")
    else:
        logger.info("Migration 007 downgrade: cycle_id is already UUID type, skipping")

