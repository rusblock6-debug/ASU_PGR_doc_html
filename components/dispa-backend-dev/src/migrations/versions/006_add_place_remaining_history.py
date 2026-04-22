"""
Добавление таблицы place_remaining_history для истории изменений остатка мест.

Revision ID: 006_add_place_remaining_history
Revises: 005
Create Date: 2025-12-15
"""

from alembic import op
import sqlalchemy as sa
from loguru import logger
from sqlalchemy.dialects import postgresql


revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade():
    """Создание таблицы place_remaining_history."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    # Проверяем, существует ли таблица
    tables = inspector.get_table_names()
    if "place_remaining_history" in tables:
        # Таблица могла быть создана по старой схеме (dev).
        # Пытаемся привести в актуальный вид без потери данных (конвертация строк → UUID).
        try:
            cols = {c["name"]: c["type"] for c in inspector.get_columns("place_remaining_history")}

            def _is_uuid(col_type) -> bool:
                # dialect UUID (postgresql.UUID) либо отраженный UUID (часто class name == "UUID")
                return isinstance(col_type, postgresql.UUID) or col_type.__class__.__name__ == "UUID"

            if "cycle_id" in cols and not _is_uuid(cols["cycle_id"]):
                op.alter_column(
                    "place_remaining_history",
                    "cycle_id",
                    existing_type=sa.String(length=100),
                    type_=postgresql.UUID(as_uuid=False),
                    existing_nullable=True,
                    postgresql_using="NULLIF(cycle_id, '')::uuid",
                )

            if "task_id" in cols and not _is_uuid(cols["task_id"]):
                op.alter_column(
                    "place_remaining_history",
                    "task_id",
                    existing_type=sa.String(length=100),
                    type_=postgresql.UUID(as_uuid=False),
                    existing_nullable=True,
                    postgresql_using="NULLIF(task_id, '')::uuid",
                )

            if "shift_id" in cols and not _is_uuid(cols["shift_id"]):
                op.alter_column(
                    "place_remaining_history",
                    "shift_id",
                    existing_type=sa.String(length=100),
                    type_=postgresql.UUID(as_uuid=False),
                    existing_nullable=True,
                    postgresql_using="NULLIF(shift_id, '')::uuid",
                )

            # Убедимся, что индексы есть
            existing_indexes = {i["name"] for i in inspector.get_indexes("place_remaining_history")}
            if "ix_place_remaining_history_cycle_id" not in existing_indexes:
                op.create_index(
                    "ix_place_remaining_history_cycle_id",
                    "place_remaining_history",
                    ["cycle_id"],
                )
            if "ix_place_remaining_history_place_id" not in existing_indexes:
                op.create_index(
                    "ix_place_remaining_history_place_id",
                    "place_remaining_history",
                    ["place_id"],
                )
            if "ix_place_remaining_history_timestamp" not in existing_indexes:
                op.create_index(
                    "ix_place_remaining_history_timestamp",
                    "place_remaining_history",
                    ["timestamp"],
                )

            logger.info(
                "Migration 006: place_remaining_history table exists, migrated schema in-place"
            )
            return
        except Exception as e:
            logger.warning(
                "Migration 006: failed to migrate place_remaining_history in-place, falling back to recreate",
                error=str(e),
            )

        # Fallback: пересоздаем в актуальной схеме.
        try:
            op.drop_index(
                "ix_place_remaining_history_place_id",
                table_name="place_remaining_history",
            )
        except Exception:
            pass
        try:
            op.drop_index(
                "ix_place_remaining_history_cycle_id",
                table_name="place_remaining_history",
            )
        except Exception:
            pass
        try:
            op.drop_index(
                "ix_place_remaining_history_timestamp",
                table_name="place_remaining_history",
            )
        except Exception:
            pass
        try:
            op.drop_table("place_remaining_history")
        except Exception:
            pass

    remaining_change_type = sa.Enum(
        "loading",
        "unloading",
        "initial",
        name="remaining_change_type",
    )

    op.create_table(
        "place_remaining_history",
        sa.Column("id", sa.String(50), nullable=False),
        sa.Column("place_id", sa.Integer(), nullable=False),
        sa.Column("change_type", remaining_change_type, nullable=False),
        sa.Column("change_amount", sa.Float(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("cycle_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("task_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("shift_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("vehicle_id", sa.String(50), nullable=True),
        sa.Column("source", sa.String(50), nullable=False, server_default="system"),
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
        sa.PrimaryKeyConstraint("id"),
    )

    # Создаем индексы
    op.create_index(
        "ix_place_remaining_history_cycle_id",
        "place_remaining_history",
        ["cycle_id"],
    )
    op.create_index(
        "ix_place_remaining_history_place_id",
        "place_remaining_history",
        ["place_id"],
    )
    op.create_index(
        "ix_place_remaining_history_timestamp",
        "place_remaining_history",
        ["timestamp"],
    )

    logger.info("Migration 006: Created place_remaining_history table with indexes")


def downgrade():
    """Удаление таблицы place_remaining_history."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    tables = inspector.get_table_names()
    if "place_remaining_history" not in tables:
        logger.info(
            "Migration 006 downgrade: place_remaining_history table does not exist, skipping"
        )
        return

    # Удаляем индексы
    try:
        op.drop_index(
            "ix_place_remaining_history_timestamp",
            table_name="place_remaining_history",
        )
    except Exception:
        pass
    try:
        op.drop_index(
            "ix_place_remaining_history_place_id",
            table_name="place_remaining_history",
        )
    except Exception:
        pass
    try:
        op.drop_index(
            "ix_place_remaining_history_cycle_id",
            table_name="place_remaining_history",
        )
    except Exception:
        pass

    # Удаляем таблицу
    op.drop_table("place_remaining_history")
    # Удаляем enum тип (если есть)
    try:
        op.execute("DROP TYPE IF EXISTS remaining_change_type")
    except Exception:
        pass
    logger.info("Migration 006 downgrade: Removed place_remaining_history table")


