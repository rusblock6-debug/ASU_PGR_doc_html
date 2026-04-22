"""Convert place dates and migrate place-node relation

Revision ID: 029
Revises: 028
Create Date: 2026-03-16
"""

from alembic import op
import sqlalchemy as sa
from geoalchemy2 import Geometry


# revision identifiers, used by Alembic.
revision = "029"
down_revision = "028"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = set(inspector.get_table_names())

    # Migrate M2M node_places -> places.node_id (one-to-one semantic).
    # If table node_places exists, pick one node per place (oldest link).
    if "places" in tables:
        place_columns = {c["name"] for c in inspector.get_columns("places")}
        # After moving Place geometry to be derived from GraphNode, allow legacy places.geometry to be NULL.
        if "geometry" in place_columns:
            op.alter_column("places", "geometry", nullable=True)
        if "node_id" not in place_columns:
            op.add_column("places", sa.Column("node_id", sa.Integer(), nullable=True))
            op.create_foreign_key(
                "fk_places_node_id_graph_nodes",
                "places",
                "graph_nodes",
                ["node_id"],
                ["id"],
                ondelete="SET NULL",
            )

    if "node_places" in tables:
        conn.execute(
            sa.text(
                """
                WITH ranked AS (
                    SELECT
                        np.place_id,
                        np.node_id,
                        ROW_NUMBER() OVER (
                            PARTITION BY np.place_id
                            ORDER BY np.created_at NULLS LAST, np.id
                        ) AS rn
                    FROM node_places np
                )
                UPDATE places p
                SET node_id = r.node_id
                FROM ranked r
                WHERE p.id = r.place_id
                  AND r.rn = 1
                  AND (p.node_id IS NULL OR p.node_id <> r.node_id)
                """
            )
        )

        # Drop indexes/constraints defensively, then remove legacy M2M table.
        op.execute(sa.text("DROP INDEX IF EXISTS ix_node_places_node_id"))
        op.execute(sa.text("DROP INDEX IF EXISTS ix_node_places_place_id"))
        op.execute(sa.text("DROP TABLE IF EXISTS node_places"))

    # Enforce one-to-one semantic: at most one place per node_id.
    # If legacy data had multiple places mapped to one node, keep the smallest place_id and null the rest.
    if "places" in tables:
        place_columns = {c["name"] for c in inspector.get_columns("places")}
        if "node_id" in place_columns:
            conn.execute(
                sa.text(
                    """
                    WITH ranked AS (
                        SELECT
                            p.id AS place_id,
                            p.node_id,
                            ROW_NUMBER() OVER (PARTITION BY p.node_id ORDER BY p.id) AS rn
                        FROM places p
                        WHERE p.node_id IS NOT NULL
                    )
                    UPDATE places p
                    SET node_id = NULL
                    FROM ranked r
                    WHERE p.id = r.place_id
                      AND r.rn > 1
                    """
                )
            )

            # Add UNIQUE constraint for node_id (Postgres allows multiple NULLs).
            op.create_unique_constraint("uq_places_node_id", "places", ["node_id"])

    # Legacy columns are no longer stored on places:
    # - geometry is derived from graph_nodes.geometry via places.node_id
    # - horizon_id is derived from graph_nodes.horizon_id via places.node_id
    if "places" in tables:
        place_columns = {c["name"] for c in inspector.get_columns("places")}
        if "horizon_id" in place_columns:
            # Default constraint name in Postgres is usually places_horizon_id_fkey.
            op.execute(sa.text("ALTER TABLE places DROP CONSTRAINT IF EXISTS places_horizon_id_fkey"))
            op.drop_column("places", "horizon_id")
        if "geometry" in place_columns:
            op.drop_column("places", "geometry")

    # place_load
    op.alter_column(
        "place_load",
        "start_date",
        existing_type=sa.DateTime(timezone=True),
        type_=sa.Date(),
        existing_nullable=False,
        postgresql_using="start_date::date",
    )
    op.alter_column(
        "place_load",
        "end_date",
        existing_type=sa.DateTime(timezone=True),
        type_=sa.Date(),
        existing_nullable=True,
        postgresql_using="end_date::date",
    )

    # place_unload
    op.alter_column(
        "place_unload",
        "start_date",
        existing_type=sa.DateTime(timezone=True),
        type_=sa.Date(),
        existing_nullable=False,
        postgresql_using="start_date::date",
    )
    op.alter_column(
        "place_unload",
        "end_date",
        existing_type=sa.DateTime(timezone=True),
        type_=sa.Date(),
        existing_nullable=True,
        postgresql_using="end_date::date",
    )

    # place_reload
    op.alter_column(
        "place_reload",
        "start_date",
        existing_type=sa.DateTime(timezone=True),
        type_=sa.Date(),
        existing_nullable=False,
        postgresql_using="start_date::date",
    )
    op.alter_column(
        "place_reload",
        "end_date",
        existing_type=sa.DateTime(timezone=True),
        type_=sa.Date(),
        existing_nullable=True,
        postgresql_using="end_date::date",
    )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = set(inspector.get_table_names())

    # place_load
    op.alter_column(
        "place_load",
        "start_date",
        existing_type=sa.Date(),
        type_=sa.DateTime(timezone=True),
        existing_nullable=False,
        postgresql_using="start_date::timestamp with time zone",
    )
    op.alter_column(
        "place_load",
        "end_date",
        existing_type=sa.Date(),
        type_=sa.DateTime(timezone=True),
        existing_nullable=True,
        postgresql_using="end_date::timestamp with time zone",
    )

    # place_unload
    op.alter_column(
        "place_unload",
        "start_date",
        existing_type=sa.Date(),
        type_=sa.DateTime(timezone=True),
        existing_nullable=False,
        postgresql_using="start_date::timestamp with time zone",
    )
    op.alter_column(
        "place_unload",
        "end_date",
        existing_type=sa.Date(),
        type_=sa.DateTime(timezone=True),
        existing_nullable=True,
        postgresql_using="end_date::timestamp with time zone",
    )

    # place_reload
    op.alter_column(
        "place_reload",
        "start_date",
        existing_type=sa.Date(),
        type_=sa.DateTime(timezone=True),
        existing_nullable=False,
        postgresql_using="start_date::timestamp with time zone",
    )
    op.alter_column(
        "place_reload",
        "end_date",
        existing_type=sa.Date(),
        type_=sa.DateTime(timezone=True),
        existing_nullable=True,
        postgresql_using="end_date::timestamp with time zone",
    )

    # Restore legacy M2M table for node-place links.
    if "node_places" not in tables:
        op.create_table(
            "node_places",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("node_id", sa.Integer(), nullable=False),
            sa.Column("place_id", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.ForeignKeyConstraint(["node_id"], ["graph_nodes.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["place_id"], ["places.id"], ondelete="CASCADE"),
            sa.UniqueConstraint("node_id", "place_id", name="uq_node_places_node_place"),
        )
        op.create_index(op.f("ix_node_places_node_id"), "node_places", ["node_id"], unique=False)
        op.create_index(op.f("ix_node_places_place_id"), "node_places", ["place_id"], unique=False)

    # Backfill node_places from places.node_id before dropping node_id.
    if "places" in tables:
        place_columns = {c["name"] for c in inspector.get_columns("places")}

        # Drop UNIQUE constraint on node_id if present.
        op.execute(sa.text("ALTER TABLE places DROP CONSTRAINT IF EXISTS uq_places_node_id"))

        # Restore legacy columns first (best-effort).
        if "geometry" not in place_columns:
            op.add_column(
                "places",
                sa.Column(
                    "geometry",
                    Geometry("POINTZ", srid=4326),
                    nullable=True,
                ),
            )
        if "horizon_id" not in place_columns:
            op.add_column(
                "places",
                sa.Column(
                    "horizon_id",
                    sa.Integer(),
                    sa.ForeignKey("horizons.id", deferrable=True, initially="IMMEDIATE"),
                    nullable=True,
                ),
            )

        # Backfill legacy columns from graph_nodes via places.node_id (best-effort).
        place_columns = {c["name"] for c in inspector.get_columns("places")}
        if "node_id" in place_columns:
            conn.execute(
                sa.text(
                    """
                    UPDATE places p
                    SET
                        geometry = gn.geometry,
                        horizon_id = gn.horizon_id
                    FROM graph_nodes gn
                    WHERE p.node_id = gn.id
                      AND (p.geometry IS NULL OR p.horizon_id IS NULL)
                    """
                )
            )

        if "node_id" in place_columns:
            conn.execute(
                sa.text(
                    """
                    INSERT INTO node_places (node_id, place_id)
                    SELECT p.node_id, p.id
                    FROM places p
                    WHERE p.node_id IS NOT NULL
                    ON CONFLICT (node_id, place_id) DO NOTHING
                    """
                )
            )

            op.execute(sa.text("ALTER TABLE places DROP CONSTRAINT IF EXISTS fk_places_node_id_graph_nodes"))
            op.drop_column("places", "node_id")

        # Restore NOT NULL on legacy places.geometry if the column exists.
        place_columns = {c["name"] for c in inspector.get_columns("places")}
        if "geometry" in place_columns:
            op.alter_column("places", "geometry", nullable=False)

