"""Convert vehicle_type and status from VARCHAR to PostgreSQL ENUM

Revision ID: 006_convert_to_enum
Revises: 005_add_vehicle_model_relationship
Create Date: 2025-12-01

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '006'
down_revision = '005'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Конвертация VARCHAR колонок в PostgreSQL ENUM.
    Существующие данные преобразуются автоматически.
    """
    
    # 1. Создаём ENUM типы
    op.execute("CREATE TYPE vehicletypeenum AS ENUM ('shas', 'pdm', 'vehicle')")
    op.execute("CREATE TYPE vehiclestatusenum AS ENUM ('active', 'maintenance', 'repair', 'inactive')")
    
    # 2. Убираем DEFAULT перед конвертацией (если есть)
    op.execute("ALTER TABLE vehicles ALTER COLUMN status DROP DEFAULT")
    
    # 3. Конвертируем vehicle_type: VARCHAR -> ENUM
    # USING преобразует существующие строковые значения в ENUM
    op.execute("""
        ALTER TABLE vehicles 
        ALTER COLUMN vehicle_type TYPE vehicletypeenum 
        USING vehicle_type::vehicletypeenum
    """)
    
    # 4. Конвертируем status: VARCHAR -> ENUM
    op.execute("""
        ALTER TABLE vehicles 
        ALTER COLUMN status TYPE vehiclestatusenum 
        USING status::vehiclestatusenum
    """)
    
    # 5. Восстанавливаем DEFAULT для status
    op.execute("ALTER TABLE vehicles ALTER COLUMN status SET DEFAULT 'active'")


def downgrade() -> None:
    """
    Откат: ENUM -> VARCHAR
    """
    
    # 1. Убираем DEFAULT
    op.execute("ALTER TABLE vehicles ALTER COLUMN status DROP DEFAULT")
    
    # 2. Конвертируем обратно в VARCHAR
    op.execute("""
        ALTER TABLE vehicles 
        ALTER COLUMN vehicle_type TYPE VARCHAR(20) 
        USING vehicle_type::text
    """)
    
    op.execute("""
        ALTER TABLE vehicles 
        ALTER COLUMN status TYPE VARCHAR(20) 
        USING status::text
    """)
    
    # 3. Восстанавливаем DEFAULT как строку
    op.execute("ALTER TABLE vehicles ALTER COLUMN status SET DEFAULT 'active'")
    
    # 4. Удаляем ENUM типы
    op.execute("DROP TYPE IF EXISTS vehiclestatusenum")
    op.execute("DROP TYPE IF EXISTS vehicletypeenum")

