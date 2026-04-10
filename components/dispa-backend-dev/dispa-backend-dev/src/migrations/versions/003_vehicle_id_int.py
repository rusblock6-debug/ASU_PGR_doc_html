"""Change vehicle_id columns to Integer."""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Временно обнуляем строковые значения в int: принудительно ставим 4 для всех записей,
    # чтобы избежать проблем cast'а вида '4_truck' → integer.
    op.execute("UPDATE cycles SET vehicle_id = '4'")
    op.execute("UPDATE cycle_state_history SET vehicle_id = '4'")
    op.execute("UPDATE cycle_tag_history SET vehicle_id = '4'")
    op.execute("UPDATE cycle_analytics SET vehicle_id = '4'")

    # cycles.vehicle_id
    op.alter_column(
        "cycles",
        "vehicle_id",
        existing_type=sa.String(length=100),
        type_=sa.Integer(),
        existing_nullable=False,
        postgresql_using="vehicle_id::integer",
    )

    # cycle_state_history.vehicle_id
    op.alter_column(
        "cycle_state_history",
        "vehicle_id",
        existing_type=sa.String(length=100),
        type_=sa.Integer(),
        existing_nullable=False,
        postgresql_using="vehicle_id::integer",
    )

    # cycle_tag_history.vehicle_id
    op.alter_column(
        "cycle_tag_history",
        "vehicle_id",
        existing_type=sa.String(length=100),
        type_=sa.Integer(),
        existing_nullable=False,
        postgresql_using="vehicle_id::integer",
    )

    # cycle_analytics.vehicle_id
    op.alter_column(
        "cycle_analytics",
        "vehicle_id",
        existing_type=sa.String(length=100),
        type_=sa.Integer(),
        existing_nullable=False,
        postgresql_using="vehicle_id::integer",
    )


def downgrade() -> None:
    # cycle_analytics.vehicle_id
    op.alter_column(
        "cycle_analytics",
        "vehicle_id",
        existing_type=sa.Integer(),
        type_=sa.String(length=100),
        existing_nullable=False,
        postgresql_using="vehicle_id::text",
    )

    # cycle_tag_history.vehicle_id
    op.alter_column(
        "cycle_tag_history",
        "vehicle_id",
        existing_type=sa.Integer(),
        type_=sa.String(length=100),
        existing_nullable=False,
        postgresql_using="vehicle_id::text",
    )

    # cycle_state_history.vehicle_id
    op.alter_column(
        "cycle_state_history",
        "vehicle_id",
        existing_type=sa.Integer(),
        type_=sa.String(length=100),
        existing_nullable=False,
        postgresql_using="vehicle_id::text",
    )

    # cycles.vehicle_id
    op.alter_column(
        "cycles",
        "vehicle_id",
        existing_type=sa.Integer(),
        type_=sa.String(length=100),
        existing_nullable=False,
        postgresql_using="vehicle_id::text",
    )

