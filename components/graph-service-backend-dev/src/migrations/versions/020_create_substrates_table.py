"""Create substrates table with opacity, center fields and nullable horizon_id

Revision ID: 020
Revises: 019
Create Date: 2026-01-27

Создает:
- Таблицу substrates (подложки для горизонтов)
- Связь один-к-одному с horizons (опциональная)
- Поля: id, horizon_id (nullable), original_filename, path_s3, opacity, center (JSONB)
- Check constraint для opacity (0-100)
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import func, text
from sqlalchemy.dialects.postgresql import JSONB
from loguru import logger

# revision identifiers, used by Alembic.
revision = "020"
down_revision = "019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()
    
    # Проверяем, существует ли таблица substrates
    if "substrates" in tables:
        logger.info("[SKIP] Table 'substrates' already exists - checking for missing fields")
        
        cols = {c["name"] for c in inspector.get_columns("substrates")}
        
        # Добавляем поле opacity, если его нет
        if "opacity" not in cols:
            op.add_column(
                "substrates",
                sa.Column("opacity", sa.Integer(), nullable=False, server_default="100")
            )
            logger.info("[OK] Added column 'opacity' to existing 'substrates' table")
            
            # Добавляем check constraint для валидации диапазона 0-100
            constraints = inspector.get_check_constraints("substrates")
            constraint_names = {c["name"] for c in constraints}
            
            if "ck_substrate_opacity_range" not in constraint_names:
                op.create_check_constraint(
                    "ck_substrate_opacity_range",
                    "substrates",
                    "opacity >= 0 AND opacity <= 100"
                )
                logger.info("[OK] Added check constraint 'ck_substrate_opacity_range' to 'substrates'")
        else:
            logger.info("[SKIP] Column 'opacity' already exists in 'substrates' - skipping")
        
        # Добавляем поле center, если его нет
        if "center" not in cols:
            op.add_column(
                "substrates",
                sa.Column(
                    "center",
                    JSONB,
                    nullable=False,
                    server_default=text("'{\"x\": 0.0, \"y\": 0.0}'::jsonb")
                )
            )
            logger.info("[OK] Added column 'center' to existing 'substrates' table")
        else:
            logger.info("[SKIP] Column 'center' already exists in 'substrates' - skipping")
        
        # Делаем horizon_id nullable, если он еще не nullable
        horizon_id_col = next((c for c in inspector.get_columns("substrates") if c["name"] == "horizon_id"), None)
        if horizon_id_col and not horizon_id_col["nullable"]:
            # Удаляем unique constraint на horizon_id, если он есть
            constraints = inspector.get_unique_constraints("substrates")
            unique_constraint = next((c for c in constraints if "horizon_id" in c["column_names"]), None)
            
            if unique_constraint:
                op.drop_constraint(unique_constraint["name"], "substrates", type_="unique")
                logger.info(f"[OK] Dropped unique constraint '{unique_constraint['name']}' from 'substrates'")
            
            # Изменяем колонку на nullable
            op.alter_column(
                "substrates",
                "horizon_id",
                nullable=True
            )
            logger.info("[OK] Changed 'horizon_id' to nullable in 'substrates'")
            
            # Восстанавливаем unique constraint
            op.create_unique_constraint(
                "uq_substrates_horizon_id",
                "substrates",
                ["horizon_id"]
            )
            logger.info("[OK] Recreated unique constraint on 'horizon_id'")
        else:
            logger.info("[SKIP] Column 'horizon_id' is already nullable - skipping")
        
        return
    
    # Создаем таблицу substrates со всеми полями (включая center и nullable horizon_id)
    op.create_table(
        'substrates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('horizon_id', sa.Integer(), nullable=True),
        sa.Column('original_filename', sa.String(length=255), nullable=False),
        sa.Column('path_s3', sa.String(length=500), nullable=False),
        sa.Column('opacity', sa.Integer(), nullable=False, server_default='100'),
        sa.Column('center', JSONB, nullable=False, server_default=text("'{\"x\": 0.0, \"y\": 0.0}'::jsonb")),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['horizon_id'], ['horizons.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('horizon_id', name='uq_substrates_horizon_id'),
        sa.CheckConstraint('opacity >= 0 AND opacity <= 100', name='ck_substrate_opacity_range')
    )
    
    # Создаем индексы
    op.create_index(op.f('ix_substrates_id'), 'substrates', ['id'], unique=False)
    op.create_index(op.f('ix_substrates_horizon_id'), 'substrates', ['horizon_id'], unique=True)
    
    logger.info("[OK] Created table 'substrates' with all fields including opacity, center and nullable horizon_id")


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()
    
    if "substrates" not in tables:
        logger.warning("[SKIP] Table 'substrates' does not exist - skipping downgrade")
        return
    
    cols = {c["name"] for c in inspector.get_columns("substrates")}
    
    # Удаляем поле center, если оно существует
    if "center" in cols:
        op.drop_column("substrates", "center")
        logger.info("[OK] Dropped column 'center' from 'substrates'")
    
    # Возвращаем horizon_id к not nullable
    horizon_id_col = next((c for c in inspector.get_columns("substrates") if c["name"] == "horizon_id"), None)
    if horizon_id_col and horizon_id_col["nullable"]:
        # Удаляем unique constraint перед изменением колонки
        constraints = inspector.get_unique_constraints("substrates")
        unique_constraint = next((c for c in constraints if "horizon_id" in c["column_names"]), None)
        
        if unique_constraint:
            op.drop_constraint(unique_constraint["name"], "substrates", type_="unique")
            logger.info(f"[OK] Dropped unique constraint '{unique_constraint['name']}' from 'substrates'")
        
        # Проверяем, есть ли NULL значения перед изменением
        result = conn.execute(sa.text("SELECT COUNT(*) FROM substrates WHERE horizon_id IS NULL"))
        null_count = result.scalar()
        
        if null_count > 0:
            logger.warning(f"[WARNING] Found {null_count} records with NULL horizon_id - setting to 0")
            # Устанавливаем временное значение для NULL записей
            conn.execute(sa.text("UPDATE substrates SET horizon_id = 0 WHERE horizon_id IS NULL"))
            conn.commit()
        
        # Изменяем колонку обратно на not nullable
        op.alter_column(
            "substrates",
            "horizon_id",
            nullable=False
        )
        logger.info("[OK] Changed 'horizon_id' back to not nullable in 'substrates'")
        
        # Восстанавливаем оригинальный unique constraint
        constraints_after = inspector.get_unique_constraints("substrates")
        existing_constraint = next((c for c in constraints_after if "horizon_id" in c["column_names"]), None)
        
        if not existing_constraint:
            op.create_unique_constraint(
                "substrates_horizon_id_key",
                "substrates",
                ["horizon_id"]
            )
            logger.info("[OK] Recreated unique constraint on 'horizon_id'")
        else:
            logger.info(f"[SKIP] Unique constraint '{existing_constraint['name']}' already exists - skipping")
    
    # Удаляем check constraint
    constraints = inspector.get_check_constraints("substrates")
    constraint_names = {c["name"] for c in constraints}
    
    if "ck_substrate_opacity_range" in constraint_names:
        op.drop_constraint("ck_substrate_opacity_range", "substrates", type_="check")
        logger.info("[OK] Dropped check constraint 'ck_substrate_opacity_range' from 'substrates'")
    
    # Удаляем поле opacity (если оно существует)
    if "opacity" in cols:
        op.drop_column("substrates", "opacity")
        logger.info("[OK] Dropped column 'opacity' from 'substrates'")
    
    # Удаляем индексы
    op.drop_index(op.f('ix_substrates_horizon_id'), table_name='substrates')
    op.drop_index(op.f('ix_substrates_id'), table_name='substrates')
    
    # Удаляем таблицу (если она была создана этой миграцией)
    op.drop_table('substrates')
    logger.info("[OK] Dropped table 'substrates'")
