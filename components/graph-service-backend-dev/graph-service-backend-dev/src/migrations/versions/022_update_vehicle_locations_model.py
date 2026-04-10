"""Update vehicle_locations and replace edge_places with node_places.

Revision ID: 022
Revises: 021
Create Date: 2026-02-11
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "022"
down_revision = "021"
branch_labels = None
depends_on = None


def _upgrade_vehicle_locations(inspector: sa.Inspector, tables: set[str]) -> None:
    if "vehicle_locations" not in tables:
        return

    cols = {c["name"] for c in inspector.get_columns("vehicle_locations")}

    if "horizon_id" not in cols:
        op.add_column(
            "vehicle_locations",
            sa.Column("horizon_id", sa.Integer(), nullable=True),
        )
        op.create_index(
            op.f("ix_vehicle_locations_horizon_id"),
            "vehicle_locations",
            ["horizon_id"],
            unique=False,
        )

        if "horizons" in tables:
            try:
                op.create_foreign_key(
                    "fk_vehicle_locations_horizon_id_horizons",
                    "vehicle_locations",
                    "horizons",
                    ["horizon_id"],
                    ["id"],
                    ondelete="SET NULL",
                )
            except Exception:
                pass

    cols = {c["name"] for c in inspector.get_columns("vehicle_locations")}
    if "height" in cols and "horizons" in tables:
        try:
            op.execute(
                sa.text(
                    """
                    UPDATE vehicle_locations vl
                    SET horizon_id = h.id
                    FROM horizons h
                    WHERE vl.horizon_id IS NULL
                      AND vl.height IS NOT NULL
                      AND h.height = vl.height
                    """
                )
            )
        except Exception:
            pass

    cols = {c["name"] for c in inspector.get_columns("vehicle_locations")}
    for col in ("lat", "lon", "height"):
        if col in cols:
            op.drop_column("vehicle_locations", col)


def _upgrade_node_places(tables: set[str]) -> None:
    if "edge_places" in tables:
        op.drop_table("edge_places")

    if "node_places" in tables:
        return

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


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = set(inspector.get_table_names())

    _upgrade_vehicle_locations(inspector, tables)
    _upgrade_node_places(tables)


def _downgrade_node_places(inspector: sa.Inspector, tables: set[str]) -> None:
    if "node_places" not in tables:
        return
    cols = {c["name"] for c in inspector.get_columns("node_places")}
    if "node_id" in cols:
        try:
            op.drop_index(op.f("ix_node_places_node_id"), table_name="node_places")
        except Exception:
            pass
    if "place_id" in cols:
        try:
            op.drop_index(op.f("ix_node_places_place_id"), table_name="node_places")
        except Exception:
            pass
    op.drop_table("node_places")


def _downgrade_vehicle_locations(inspector: sa.Inspector, tables: set[str]) -> None:
    if "vehicle_locations" not in tables:
        return

    cols = {c["name"] for c in inspector.get_columns("vehicle_locations")}
    if "lat" not in cols:
        op.add_column("vehicle_locations", sa.Column("lat", sa.Float(), nullable=True))
    if "lon" not in cols:
        op.add_column("vehicle_locations", sa.Column("lon", sa.Float(), nullable=True))
    if "height" not in cols:
        op.add_column("vehicle_locations", sa.Column("height", sa.Float(), nullable=True))

    try:
        op.execute(
            sa.text(
                "UPDATE vehicle_locations SET lat = ST_Y(geometry), lon = ST_X(geometry) "
                "WHERE geometry IS NOT NULL"
            )
        )
    except Exception:
        pass

    cols = {c["name"] for c in inspector.get_columns("vehicle_locations")}
    if "horizon_id" in cols:
        try:
            op.drop_constraint(
                "fk_vehicle_locations_horizon_id_horizons",
                "vehicle_locations",
                type_="foreignkey",
            )
        except Exception:
            pass
        try:
            op.drop_index(op.f("ix_vehicle_locations_horizon_id"), table_name="vehicle_locations")
        except Exception:
            pass
        op.drop_column("vehicle_locations", "horizon_id")


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = set(inspector.get_table_names())

    _downgrade_node_places(inspector, tables)
    _downgrade_vehicle_locations(inspector, tables)


