"""
Обновление enum remaining_change_type для place_remaining_history:
- добавляем тип manual
- убираем initial (данные initial маппим в manual)

Revision ID: 017
Revises: 016
Create Date: 2026-02-11
"""

from alembic import op
import sqlalchemy as sa
from loguru import logger


revision = "017"
down_revision = "016"
branch_labels = None
depends_on = None


def _get_enum_labels(conn, enum_name: str) -> list[str]:
    rows = conn.execute(
        sa.text(
            """
            SELECT e.enumlabel
            FROM pg_type t
            JOIN pg_enum e ON t.oid = e.enumtypid
            WHERE t.typname = :enum_name
            ORDER BY e.enumsortorder
            """
        ),
        {"enum_name": enum_name},
    ).fetchall()
    return [r[0] for r in rows]


def upgrade():
    conn = op.get_bind()

    # Если типа нет — ничего не делаем (на всякий случай, для dev/неполных окружений)
    try:
        labels = _get_enum_labels(conn, "remaining_change_type")
    except Exception as e:
        logger.warning(
            "Migration 017: failed to inspect remaining_change_type, skipping",
            error=str(e),
        )
        return

    desired = ["loading", "unloading", "manual"]
    enum_changed = False
    if labels != desired:
        # 1) создаём новый enum без initial и переводим колонку.
        # Маппинг initial -> manual делаем в USING без промежуточного ADD VALUE.
        op.execute("DROP TYPE IF EXISTS remaining_change_type_new")
        op.execute("CREATE TYPE remaining_change_type_new AS ENUM ('loading', 'unloading', 'manual')")
        op.execute(
            """
            ALTER TABLE place_remaining_history
            ALTER COLUMN change_type
            TYPE remaining_change_type_new
            USING (
                CASE
                    WHEN change_type::text = 'initial' THEN 'manual'
                    ELSE change_type::text
                END
            )::remaining_change_type_new
            """
        )

        # 2) меняем типы местами
        op.execute("DROP TYPE remaining_change_type")
        op.execute("ALTER TYPE remaining_change_type_new RENAME TO remaining_change_type")
        enum_changed = True

    # 5) vehicle_id nullable
    vehicle_id_changed = False
    try:
        inspector = sa.inspect(conn)
        tables = inspector.get_table_names()
        if "place_remaining_history" in tables:
            cols = {c["name"]: c for c in inspector.get_columns("place_remaining_history")}
            if "vehicle_id" in cols and not cols["vehicle_id"].get("nullable", True):
                op.alter_column(
                    "place_remaining_history",
                    "vehicle_id",
                    existing_type=cols["vehicle_id"]["type"],
                    nullable=True,
                )
                vehicle_id_changed = True
    except Exception as e:
        logger.warning("Migration 017: failed to make vehicle_id nullable (non-critical)", error=str(e))

    logger.info(
        "Migration 017 completed",
        enum_changed=enum_changed,
        vehicle_id_nullable_changed=vehicle_id_changed,
    )


def downgrade():
    # Downgrade: возвращаем initial, убираем manual (manual -> initial).
    # Это потенциально теряет семантику, но позволяет откатить миграцию.
    conn = op.get_bind()

    try:
        labels = _get_enum_labels(conn, "remaining_change_type")
    except Exception as e:
        logger.warning(
            "Migration 017 downgrade: failed to inspect remaining_change_type, skipping",
            error=str(e),
        )
        return

    desired = ["loading", "unloading", "initial"]
    enum_changed = False
    if labels != desired:
        # 1) создаём новый enum без manual и переводим колонку.
        # Маппинг manual -> initial делаем в USING без промежуточного ADD VALUE.
        op.execute("DROP TYPE IF EXISTS remaining_change_type_old")
        op.execute("CREATE TYPE remaining_change_type_old AS ENUM ('loading', 'unloading', 'initial')")
        op.execute(
            """
            ALTER TABLE place_remaining_history
            ALTER COLUMN change_type
            TYPE remaining_change_type_old
            USING (
                CASE
                    WHEN change_type::text = 'manual' THEN 'initial'
                    ELSE change_type::text
                END
            )::remaining_change_type_old
            """
        )

        op.execute("DROP TYPE remaining_change_type")
        op.execute("ALTER TYPE remaining_change_type_old RENAME TO remaining_change_type")
        enum_changed = True

    # 4) откат vehicle_id nullable (объединено из миграции 018)
    vehicle_id_changed = False
    try:
        inspector = sa.inspect(conn)
        tables = inspector.get_table_names()
        if "place_remaining_history" in tables:
            cols = {c["name"]: c for c in inspector.get_columns("place_remaining_history")}
            if "vehicle_id" in cols and cols["vehicle_id"].get("nullable", False):
                try:
                    op.execute(
                        "UPDATE place_remaining_history SET vehicle_id = 0 WHERE vehicle_id IS NULL"
                    )
                except Exception:
                    pass
                op.alter_column(
                    "place_remaining_history",
                    "vehicle_id",
                    existing_type=cols["vehicle_id"]["type"],
                    nullable=False,
                )
                vehicle_id_changed = True
    except Exception:
        pass

    logger.info(
        "Migration 017 downgrade completed",
        enum_changed=enum_changed,
        vehicle_id_not_null_changed=vehicle_id_changed,
    )


