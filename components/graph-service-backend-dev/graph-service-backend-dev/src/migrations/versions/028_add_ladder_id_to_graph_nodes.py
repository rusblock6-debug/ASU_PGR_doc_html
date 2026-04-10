"""Create ladders and node_ladders tables

Revision ID: 028
Revises: 027
Create Date: 2026-03-13 12:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "028"
down_revision = "027"
branch_labels = None
depends_on = None

# Имя новой ассоциативной таблицы
NODE_LADDERS_TABLE = "node_ladders"


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    tables = set(inspector.get_table_names())


    # 1. Создаём таблицу ladders (если её ещё нет)
    if "ladders" not in tables:
        op.create_table(
            "ladders",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("from_horizon_id", sa.Integer(), nullable=False),
            sa.Column("to_horizon_id", sa.Integer(), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("is_completed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.ForeignKeyConstraint(
                ["from_horizon_id"],
                ["horizons.id"],
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["to_horizon_id"],
                ["horizons.id"],
                ondelete="CASCADE",
            ),
        )
        op.create_index("ix_ladders_from_horizon_id", "ladders", ["from_horizon_id"])
        op.create_index("ix_ladders_to_horizon_id", "ladders", ["to_horizon_id"])

    # 2. Создаём ассоциативную таблицу node_ladders (если её ещё нет)
    if NODE_LADDERS_TABLE not in tables:
        op.create_table(
            NODE_LADDERS_TABLE,
            sa.Column("node_id", sa.Integer(), nullable=False),
            sa.Column("ladder_id", sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(
                ["node_id"],
                ["graph_nodes.id"],
                deferrable=True,
                initially="IMMEDIATE",
            ),
            sa.ForeignKeyConstraint(
                ["ladder_id"],
                ["ladders.id"],
                deferrable=True,
                initially="IMMEDIATE",
            ),
            sa.PrimaryKeyConstraint("node_id", "ladder_id"),
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = set(inspector.get_table_names())

    # Удаляем ассоциативную таблицу
    if NODE_LADDERS_TABLE in tables:
        op.drop_table(NODE_LADDERS_TABLE)

    # И таблицу ladders
    if "ladders" in tables:
        op.drop_index("ix_ladders_from_horizon_id", table_name="ladders")
        op.drop_index("ix_ladders_to_horizon_id", table_name="ladders")
        op.drop_table("ladders")
