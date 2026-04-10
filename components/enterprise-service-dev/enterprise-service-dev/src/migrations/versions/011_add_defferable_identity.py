"""add defferable identity

Revision ID: 011
Revises: 010
Create Date: 2026-01-30 12:14:42.240665

"""
from alembic import op
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision = '011'
down_revision = '010'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Make all foreign keys DEFERRABLE INITIALLY IMMEDIATE."""

    # work_regimes.enterprise_id -> enterprise_settings.id
    op.drop_constraint('work_regimes_enterprise_id_fkey', 'work_regimes', type_='foreignkey')
    op.execute(text("""
        ALTER TABLE work_regimes
        ADD CONSTRAINT work_regimes_enterprise_id_fkey
        FOREIGN KEY (enterprise_id)
        REFERENCES enterprise_settings(id)
        DEFERRABLE INITIALLY IMMEDIATE
    """))

    # vehicles.enterprise_id -> enterprise_settings.id
    op.drop_constraint('vehicles_enterprise_id_fkey', 'vehicles', type_='foreignkey')
    op.execute(text("""
        ALTER TABLE vehicles
        ADD CONSTRAINT vehicles_enterprise_id_fkey
        FOREIGN KEY (enterprise_id)
        REFERENCES enterprise_settings(id)
        DEFERRABLE INITIALLY IMMEDIATE
    """))

    # vehicles.model_id -> vehicle_models.id
    op.drop_constraint('fk_vehicles_model_id', 'vehicles', type_='foreignkey')
    op.execute(text("""
        ALTER TABLE vehicles
        ADD CONSTRAINT fk_vehicles_model_id
        FOREIGN KEY (model_id)
        REFERENCES vehicle_models(id)
        DEFERRABLE INITIALLY IMMEDIATE
    """))

    # shift_tasks.vehicle_id -> vehicles.id
    op.drop_constraint('shift_tasks_vehicle_id_fkey', 'shift_tasks', type_='foreignkey')
    op.execute(text("""
        ALTER TABLE shift_tasks
        ADD CONSTRAINT shift_tasks_vehicle_id_fkey
        FOREIGN KEY (vehicle_id)
        REFERENCES vehicles(id)
        DEFERRABLE INITIALLY IMMEDIATE
    """))

    # shift_tasks.work_regime_id -> work_regimes.id
    op.drop_constraint('shift_tasks_work_regime_id_fkey', 'shift_tasks', type_='foreignkey')
    op.execute(text("""
        ALTER TABLE shift_tasks
        ADD CONSTRAINT shift_tasks_work_regime_id_fkey
        FOREIGN KEY (work_regime_id)
        REFERENCES work_regimes(id)
        DEFERRABLE INITIALLY IMMEDIATE
    """))

    # route_tasks.shift_task_id -> shift_tasks.id (with ON DELETE CASCADE)
    op.drop_constraint('route_tasks_shift_task_id_fkey', 'route_tasks', type_='foreignkey')
    op.execute(text("""
        ALTER TABLE route_tasks
        ADD CONSTRAINT route_tasks_shift_task_id_fkey
        FOREIGN KEY (shift_task_id)
        REFERENCES shift_tasks(id)
        ON DELETE CASCADE
        DEFERRABLE INITIALLY IMMEDIATE
    """))

    # statuses.organization_category_id -> organization_categories.id
    op.drop_constraint('fk_statuses_organization_category', 'statuses', type_='foreignkey')
    op.execute(text("""
        ALTER TABLE statuses
        ADD CONSTRAINT fk_statuses_organization_category
        FOREIGN KEY (organization_category_id)
        REFERENCES organization_categories(id)
        DEFERRABLE INITIALLY IMMEDIATE
    """))

    # load_types.category_id -> load_type_categories.id (with ON DELETE RESTRICT)
    op.drop_constraint('load_types_category_id_fkey', 'load_types', type_='foreignkey')
    op.execute(text("""
        ALTER TABLE load_types
        ADD CONSTRAINT load_types_category_id_fkey
        FOREIGN KEY (category_id)
        REFERENCES load_type_categories(id)
        ON DELETE RESTRICT
        DEFERRABLE INITIALLY IMMEDIATE
    """))


def downgrade() -> None:
    """Revert foreign keys to non-deferrable state."""

    # work_regimes.enterprise_id -> enterprise_settings.id
    op.drop_constraint('work_regimes_enterprise_id_fkey', 'work_regimes', type_='foreignkey')
    op.execute(text("""
        ALTER TABLE work_regimes
        ADD CONSTRAINT work_regimes_enterprise_id_fkey
        FOREIGN KEY (enterprise_id)
        REFERENCES enterprise_settings(id)
    """))

    # vehicles.enterprise_id -> enterprise_settings.id
    op.drop_constraint('vehicles_enterprise_id_fkey', 'vehicles', type_='foreignkey')
    op.execute(text("""
        ALTER TABLE vehicles
        ADD CONSTRAINT vehicles_enterprise_id_fkey
        FOREIGN KEY (enterprise_id)
        REFERENCES enterprise_settings(id)
    """))

    # vehicles.model_id -> vehicle_models.id
    op.drop_constraint('fk_vehicles_model_id', 'vehicles', type_='foreignkey')
    op.execute(text("""
        ALTER TABLE vehicles
        ADD CONSTRAINT fk_vehicles_model_id
        FOREIGN KEY (model_id)
        REFERENCES vehicle_models(id)
    """))

    # shift_tasks.vehicle_id -> vehicles.id
    op.drop_constraint('shift_tasks_vehicle_id_fkey', 'shift_tasks', type_='foreignkey')
    op.execute(text("""
        ALTER TABLE shift_tasks
        ADD CONSTRAINT shift_tasks_vehicle_id_fkey
        FOREIGN KEY (vehicle_id)
        REFERENCES vehicles(id)
    """))

    # shift_tasks.work_regime_id -> work_regimes.id
    op.drop_constraint('shift_tasks_work_regime_id_fkey', 'shift_tasks', type_='foreignkey')
    op.execute(text("""
        ALTER TABLE shift_tasks
        ADD CONSTRAINT shift_tasks_work_regime_id_fkey
        FOREIGN KEY (work_regime_id)
        REFERENCES work_regimes(id)
    """))

    # route_tasks.shift_task_id -> shift_tasks.id (with ON DELETE CASCADE)
    op.drop_constraint('route_tasks_shift_task_id_fkey', 'route_tasks', type_='foreignkey')
    op.execute(text("""
        ALTER TABLE route_tasks
        ADD CONSTRAINT route_tasks_shift_task_id_fkey
        FOREIGN KEY (shift_task_id)
        REFERENCES shift_tasks(id)
        ON DELETE CASCADE
    """))

    # statuses.organization_category_id -> organization_categories.id
    op.drop_constraint('fk_statuses_organization_category', 'statuses', type_='foreignkey')
    op.execute(text("""
        ALTER TABLE statuses
        ADD CONSTRAINT fk_statuses_organization_category
        FOREIGN KEY (organization_category_id)
        REFERENCES organization_categories(id)
    """))

    # load_types.category_id -> load_type_categories.id (with ON DELETE RESTRICT)
    op.drop_constraint('load_types_category_id_fkey', 'load_types', type_='foreignkey')
    op.execute(text("""
        ALTER TABLE load_types
        ADD CONSTRAINT load_types_category_id_fkey
        FOREIGN KEY (category_id)
        REFERENCES load_type_categories(id)
        ON DELETE RESTRICT
    """))
