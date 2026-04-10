"""Refactor Status model: remove fields, add OrganizationCategory, add AnalyticCategoryEnum

Revision ID: 007_refactor_status_model
Revises: 006_convert_to_enum
Create Date: 2025-12-02

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '007'
down_revision = '006'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Рефакторинг модели Status:
    1. Создаём таблицу organization_categories
    2. Создаём ENUM для analytic_category
    3. Удаляем ненужные колонки из statuses
    4. Добавляем FK на organization_categories
    5. Конвертируем analytic_category в ENUM
    """
    
    # 1. Создаём таблицу organization_categories
    op.create_table(
        'organization_categories',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(100), nullable=False, unique=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # 2. Создаём ENUM тип для analytic_category
    op.execute("""
        CREATE TYPE analyticcategoryenum AS ENUM (
            'productive',
            'non_productive',
            'work_delays',
            'external_causes',
            'planned_maintenance',
            'unplanned_maintenance',
            'unscheduled_time'
        )
    """)
    
    # 3. Удаляем ненужные колонки из statuses
    op.drop_column('statuses', 'enterprise_id')
    op.drop_column('statuses', 'export_code')
    op.drop_column('statuses', 'description')
    op.drop_column('statuses', 'status_category')
    op.drop_column('statuses', 'available_vehicle_types')
    op.drop_column('statuses', 'is_plan')
    op.drop_column('statuses', 'standard_duration')
    op.drop_column('statuses', 'is_active')
    
    # 4. Удаляем старую колонку organization_category (VARCHAR)
    op.drop_column('statuses', 'organization_category')
    
    # 5. Переименовываем name в display_name
    op.alter_column('statuses', 'name', new_column_name='display_name')
    
    # 6. Добавляем колонку system_name (уникальное)
    op.add_column(
        'statuses',
        sa.Column('system_name', sa.String(100), nullable=True)
    )
    # Заполняем system_name из display_name для существующих записей
    op.execute("UPDATE statuses SET system_name = display_name WHERE system_name IS NULL")
    op.add_column('statuses', sa.Column('system_status', sa.Boolean(), nullable=False, server_default='false'))
    # Делаем NOT NULL и UNIQUE
    op.execute("ALTER TABLE statuses ALTER COLUMN system_name SET NOT NULL")
    op.create_unique_constraint('uq_statuses_system_name', 'statuses', ['system_name'])
    
    # 7. Добавляем новую колонку organization_category_id с FK
    op.add_column(
        'statuses',
        sa.Column('organization_category_id', sa.Integer(), nullable=True)
    )
    op.create_foreign_key(
        'fk_statuses_organization_category',
        'statuses',
        'organization_categories',
        ['organization_category_id'],
        ['id']
    )
    
    # 8. Конвертируем analytic_category из VARCHAR в ENUM
    # Сначала обновляем NULL значения на дефолтное
    op.execute("UPDATE statuses SET analytic_category = 'productive' WHERE analytic_category IS NULL OR analytic_category = ''")
    
    # Конвертируем колонку
    op.execute("""
        ALTER TABLE statuses 
        ALTER COLUMN analytic_category TYPE analyticcategoryenum 
        USING analytic_category::analyticcategoryenum
    """)
    
    # Устанавливаем NOT NULL и DEFAULT
    op.execute("ALTER TABLE statuses ALTER COLUMN analytic_category SET NOT NULL")
    op.execute("ALTER TABLE statuses ALTER COLUMN analytic_category SET DEFAULT 'productive'")

    # Миграция данных
    upgrade_data()


def upgrade_data() -> None:
    """
    Миграция данных: добавление категории и статусов.
    """
    from sqlalchemy import text
    
    # Добавляем организационную категорию "Технологическая" (если её нет)
    op.execute("""
        INSERT INTO organization_categories (name, created_at, updated_at)
        VALUES ('Технологическая', NOW(), NOW())
        ON CONFLICT (name) DO NOTHING
    """)

    # Получаем ID категории "Технологическая"
    conn = op.get_bind()
    result = conn.execute(text("SELECT id FROM organization_categories WHERE name = 'Технологическая'"))
    category_row = result.fetchone()
    
    if category_row:
        category_id = category_row[0]

        # Добавляем статусы (system_name на латинице, display_name на кириллице)
        statuses_data = [
            ('idle', 'Ожидание погрузки', '#FFFC29'),
            ('loading', 'Погрузка', '#EB74B2'),
            ('moving_loaded', 'Движение гружёным', '#87F915'),
            ('stopped_loaded', 'Остановка гружёным', '#7EE006'),
            ('unloading', 'Разгрузка', '#E6E7E4'),
            ('moving_empty', 'Движение порожним', '#BECAE0'),
            ('stopped_empty', 'Остановка порожним', '#9EB0D1'),
        ]

        for system_name, display_name, color in statuses_data:
            op.execute(f"""
                INSERT INTO statuses (system_name, display_name, color, analytic_category, organization_category_id, system_status, created_at, updated_at)
                VALUES ('{system_name}', '{display_name}', '{color}', 'productive', {category_id}, true, NOW(), NOW())
                ON CONFLICT (system_name) DO NOTHING
            """)


def downgrade() -> None:
    """
    Откат изменений:
    1. Удаляем system_name и переименовываем display_name обратно в name
    2. Конвертируем analytic_category обратно в VARCHAR
    3. Удаляем FK и колонку organization_category_id
    4. Восстанавливаем старые колонки
    5. Удаляем таблицу organization_categories
    6. Удаляем ENUM тип
    """
    
    # 1. Удаляем system_name
    op.drop_constraint('uq_statuses_system_name', 'statuses', type_='unique')
    op.drop_column('statuses', 'system_name')
    
    # 2. Переименовываем display_name обратно в name
    op.alter_column('statuses', 'display_name', new_column_name='name')
    
    # 3. Убираем DEFAULT и NOT NULL для analytic_category
    op.execute("ALTER TABLE statuses ALTER COLUMN analytic_category DROP DEFAULT")
    op.execute("ALTER TABLE statuses ALTER COLUMN analytic_category DROP NOT NULL")
    
    # 4. Конвертируем analytic_category обратно в VARCHAR
    op.execute("""
        ALTER TABLE statuses 
        ALTER COLUMN analytic_category TYPE VARCHAR(50) 
        USING analytic_category::text
    """)
    
    # 5. Удаляем FK и колонку organization_category_id
    op.drop_constraint('fk_statuses_organization_category', 'statuses', type_='foreignkey')
    op.drop_column('statuses', 'organization_category_id')
    op.drop_column('statuses', 'system_status')
    
    # 6. Восстанавливаем старую колонку organization_category
    op.add_column(
        'statuses',
        sa.Column('organization_category', sa.String(50), nullable=True)
    )
    
    # 7. Восстанавливаем удалённые колонки
    op.add_column('statuses', sa.Column('enterprise_id', sa.Integer(), nullable=False, server_default='1'))
    op.add_column('statuses', sa.Column('export_code', sa.String(50), nullable=True, unique=True))
    op.add_column('statuses', sa.Column('description', sa.Text(), nullable=True))
    op.add_column('statuses', sa.Column('status_category', sa.String(50), nullable=True))
    op.add_column('statuses', sa.Column('available_vehicle_types', sa.String(50), nullable=True))
    op.add_column('statuses', sa.Column('is_plan', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('statuses', sa.Column('standard_duration', sa.Integer(), nullable=True))
    op.add_column('statuses', sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'))
    
    # Убираем server_default
    op.execute("ALTER TABLE statuses ALTER COLUMN system_status DROP DEFAULT")
    op.execute("ALTER TABLE statuses ALTER COLUMN enterprise_id DROP DEFAULT")
    op.execute("ALTER TABLE statuses ALTER COLUMN is_plan DROP DEFAULT")
    op.execute("ALTER TABLE statuses ALTER COLUMN is_active DROP DEFAULT")
    
    # Создаём FK для enterprise_id
    op.create_foreign_key(
        'fk_statuses_enterprise',
        'statuses',
        'enterprise_settings',
        ['enterprise_id'],
        ['id']
    )
    
    # 8. Удаляем таблицу organization_categories
    op.drop_table('organization_categories')
    
    # 9. Удаляем ENUM тип
    op.execute("DROP TYPE IF EXISTS analyticcategoryenum")

