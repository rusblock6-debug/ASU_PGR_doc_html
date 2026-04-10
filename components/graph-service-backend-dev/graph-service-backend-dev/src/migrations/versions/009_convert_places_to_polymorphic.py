"""Convert places to polymorphic structure (JTI) - Squashed migrations 006, 007, 008

Revision ID: 009
Revises: 008
Create Date: 2025-01-XX XX:XX:XX
"""
from datetime import datetime as dt
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '009'
down_revision = '008'
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    
    # 1. Изменяем длину колонки type с 20 на 50
    op.alter_column('places', 'type', type_=sa.String(length=20))
    
    # Также изменяем длину колонки name с 100 на 255
    op.alter_column('places', 'name', type_=sa.String(length=255))
    
    # Создаем индекс для type (в модели указан index=True)
    op.create_index(op.f('ix_places_type'), 'places', ['type'], unique=False)
    
    # 3. Создаем таблицы для подклассов (JTI)
    op.create_table(
        'place_load',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('start_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('end_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('initial_stock', sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(['id'], ['places.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_table(
        'place_unload',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('start_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('end_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('capacity', sa.Float(), nullable=True),
        sa.Column('current_stock', sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(['id'], ['places.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_table(
        'place_reload',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('start_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('end_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('capacity', sa.Float(), nullable=True),
        sa.Column('current_stock', sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(['id'], ['places.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # 5. Переносим данные из старых колонок places в новые таблицы подклассов
    # Loading places (из primary_remainder -> initial_stock, active_from/active_to -> start_date/end_date)
    # Вставляем записи для всех load мест, даже если данные NULL
    loading_result = connection.execute(sa.text("""
        SELECT id, active_from, active_to, primary_remainder, updated_at
        FROM places
        WHERE type = 'load'
    """))
    
    for row in loading_result.fetchall():
        place_id = row[0]
        active_from = row[1]  # Date
        active_to = row[2]  # Date
        primary_remainder = row[3]
        
        # Конвертируем Date в DateTime для start_date и end_date
        start_date = None
        end_date = None
        if active_from:
            # Конвертируем date в datetime (начало дня)
            start_date = dt.combine(active_from, dt.min.time())
        if active_to:
            end_date = dt.combine(active_to, dt.min.time())
        
        connection.execute(sa.text("""
            INSERT INTO place_load (id, start_date, end_date, initial_stock)
            VALUES (:id, :start_date, :end_date, :initial_stock)
        """), {
            "id": place_id,
            "start_date": start_date,
            "end_date": end_date,
            "initial_stock": primary_remainder,
        })
    
    # Unloading places (из capacity, remainder -> capacity, current_stock)
    # Примечание: в старой схеме не было поля remainder, поэтому current_stock будет NULL
    # Вставляем записи для всех unload мест, даже если данные NULL
    unloading_result = connection.execute(sa.text("""
        SELECT id, active_from, active_to, capacity, updated_at
        FROM places
        WHERE type = 'unload'
    """))
    
    for row in unloading_result.fetchall():
        place_id = row[0]
        active_from = row[1]  # Date
        active_to = row[2]  # Date
        capacity = row[3]
        
        # Конвертируем Date в DateTime для start_date и end_date
        start_date = None
        end_date = None
        if active_from:
            start_date = dt.combine(active_from, dt.min.time())
        if active_to:
            end_date = dt.combine(active_to, dt.min.time())
        
        connection.execute(sa.text("""
            INSERT INTO place_unload (id, start_date, end_date, capacity, current_stock)
            VALUES (:id, :start_date, :end_date, :capacity, :current_stock)
        """), {
            "id": place_id,
            "start_date": start_date,
            "end_date": end_date,
            "capacity": capacity,
            "current_stock": None,  # В старой схеме не было remainder
        })
    
    # Reload places (перегрузка) - аналогично unloading
    # Вставляем записи для всех reload мест, даже если данные NULL
    reload_result = connection.execute(sa.text("""
        SELECT id, active_from, active_to, capacity, updated_at
        FROM places
        WHERE type = 'reload'
    """))
    
    for row in reload_result.fetchall():
        place_id = row[0]
        active_from = row[1]  # Date
        active_to = row[2]  # Date
        capacity = row[3]
        
        # Конвертируем Date в DateTime для start_date и end_date
        start_date = None
        end_date = None
        if active_from:
            start_date = dt.combine(active_from, dt.min.time())
        if active_to:
            end_date = dt.combine(active_to, dt.min.time())
        
        connection.execute(sa.text("""
            INSERT INTO place_reload (id, start_date, end_date, capacity, current_stock)
            VALUES (:id, :start_date, :end_date, :capacity, :current_stock)
        """), {
            "id": place_id,
            "start_date": start_date,
            "end_date": end_date,
            "capacity": capacity,
            "current_stock": None,  # В старой схеме не было remainder
        })
    
    # Parking и Transit places используют базовый класс Place, поэтому не создаем для них отдельные таблицы
    
    # 6. Удаляем старые колонки из places
    op.drop_column('places', 'available_vehicle_types')
    op.drop_column('places', 'capacity')
    op.drop_column('places', 'active_from')
    op.drop_column('places', 'active_to')
    op.drop_column('places', 'is_active')
    op.drop_column('places', 'primary_remainder')


def downgrade() -> None:
    connection = op.get_bind()
    
    # 1. Восстанавливаем колонки в places
    op.add_column('places', sa.Column('available_vehicle_types', sa.String(length=50), nullable=True))
    op.add_column('places', sa.Column('capacity', sa.Float(), nullable=True))
    op.add_column('places', sa.Column('active_from', sa.Date(), nullable=True))
    op.add_column('places', sa.Column('active_to', sa.Date(), nullable=True))
    op.add_column('places', sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')))
    op.add_column('places', sa.Column('primary_remainder', sa.Float(), nullable=True))
    
    # 2. Переносим данные обратно из таблиц подклассов в places
    # Loading places
    loading_result = connection.execute(sa.text("""
        SELECT id, start_date, end_date, initial_stock
        FROM place_load
    """))
    
    for row in loading_result.fetchall():
        place_id = row[0]
        start_date = row[1]
        end_date = row[2]
        initial_stock = row[3]
        
        # Конвертируем DateTime в Date для active_from и active_to
        active_from = start_date.date() if start_date else None
        active_to = end_date.date() if end_date else None
        
        connection.execute(sa.text("""
            UPDATE places 
            SET active_from = :active_from,
                active_to = :active_to,
                primary_remainder = :primary_remainder,
                updated_at = :updated_at
            WHERE id = :place_id
        """), {
            "place_id": place_id,
            "active_from": active_from,
            "active_to": active_to,
            "primary_remainder": initial_stock,
        })
    
    # Unloading places
    unloading_result = connection.execute(sa.text("""
        SELECT id, start_date, end_date, capacity, current_stock
        FROM place_unload
    """))
    
    for row in unloading_result.fetchall():
        place_id = row[0]
        start_date = row[1]
        end_date = row[2]
        capacity = row[3]
        current_stock = row[4]
        
        active_from = start_date.date() if start_date else None
        active_to = end_date.date() if end_date else None
        
        connection.execute(sa.text("""
            UPDATE places 
            SET active_from = :active_from,
                active_to = :active_to,
                capacity = :capacity,
                updated_at = :updated_at
            WHERE id = :place_id
        """), {
            "place_id": place_id,
            "active_from": active_from,
            "active_to": active_to,
            "capacity": capacity,
        })
    
    # Reload places -> аналогично unloading
    reload_result = connection.execute(sa.text("""
        SELECT id, start_date, end_date, capacity, current_stock
        FROM place_reload
    """))
    
    for row in reload_result.fetchall():
        place_id = row[0]
        start_date = row[1]
        end_date = row[2]
        capacity = row[3]
        current_stock = row[4]
        
        active_from = start_date.date() if start_date else None
        active_to = end_date.date() if end_date else None
        
        connection.execute(sa.text("""
            UPDATE places 
            SET active_from = :active_from,
                active_to = :active_to,
                capacity = :capacity,
                updated_at = :updated_at
            WHERE id = :place_id
        """), {
            "place_id": place_id,
            "active_from": active_from,
            "active_to": active_to,
            "capacity": capacity,
        })
    
    # 3. Удаляем таблицы подклассов
    op.drop_table('place_reload')
    op.drop_table('place_unload')
    op.drop_table('place_load')
    
    # 4. Удаляем индекс для type
    op.drop_index(op.f('ix_places_type'), table_name='places')
    
    # 7. Восстанавливаем длину колонок
    op.alter_column('places', 'type', type_=sa.String(length=20))
    op.alter_column('places', 'name', type_=sa.String(length=100))

