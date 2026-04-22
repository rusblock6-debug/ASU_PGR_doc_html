"""Convert places.type from VARCHAR to ENUM

Revision ID: 013
Revises: 012
Create Date: 2025-12-12
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '013'
down_revision = '012'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Создаём ENUM тип place_type (если не существует)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE place_type AS ENUM ('load', 'unload', 'reload', 'transit', 'park');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    # 2. Конвертируем колонку type из VARCHAR в ENUM
    op.execute("""
        ALTER TABLE places 
        ALTER COLUMN type TYPE place_type 
        USING type::place_type;
    """)


def downgrade() -> None:
    # 1. Конвертируем колонку обратно в VARCHAR
    op.execute("""
        ALTER TABLE places 
        ALTER COLUMN type TYPE VARCHAR(20) 
        USING type::text;
    """)
    
    # 2. Удаляем ENUM тип (опционально, может использоваться в других местах)
    # op.execute("DROP TYPE IF EXISTS place_type;")

