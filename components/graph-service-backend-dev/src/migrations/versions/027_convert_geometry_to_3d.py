"""Convert geometry columns to 3D (POINTZ/LINESTRINGZ).

Revision ID: 027
Revises: 026
Create Date: 2026-03-05
"""

from alembic import op
import sqlalchemy as sa
from geoalchemy2 import Geometry


# revision identifiers, used by Alembic.
revision = "027"
down_revision = "026"
branch_labels = None
depends_on = None


def _has_column(inspector: sa.Inspector, table_name: str, column_name: str) -> bool:
    return any(col["name"] == column_name for col in inspector.get_columns(table_name))


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = set(inspector.get_table_names())

    if "graph_nodes" in tables and _has_column(inspector, "graph_nodes", "geometry"):
        op.alter_column(
            "graph_nodes",
            "geometry",
            existing_type=Geometry("POINT", srid=4326),
            type_=Geometry("POINTZ", srid=4326),
            postgresql_using="ST_Force3DZ(geometry)",
        )
        if "horizons" in tables and _has_column(inspector, "graph_nodes", "horizon_id"):
            op.execute(
                sa.text(
                    """
                    UPDATE graph_nodes AS gn
                    SET geometry = ST_SetSRID(
                        ST_MakePoint(
                            ST_X(gn.geometry),
                            ST_Y(gn.geometry),
                            h.height
                        ),
                        4326
                    )
                    FROM horizons AS h
                    WHERE h.id = gn.horizon_id
                      AND gn.geometry IS NOT NULL
                    """
                )
            )

    if "places" in tables and _has_column(inspector, "places", "geometry"):
        op.alter_column(
            "places",
            "geometry",
            existing_type=Geometry("POINT", srid=4326),
            type_=Geometry("POINTZ", srid=4326),
            postgresql_using="ST_Force3DZ(geometry)",
        )
        if "horizons" in tables and _has_column(inspector, "places", "horizon_id"):
            op.execute(
                sa.text(
                    """
                    UPDATE places AS p
                    SET geometry = ST_SetSRID(
                        ST_MakePoint(
                            ST_X(p.geometry),
                            ST_Y(p.geometry),
                            h.height
                        ),
                        4326
                    )
                    FROM horizons AS h
                    WHERE h.id = p.horizon_id
                      AND p.geometry IS NOT NULL
                    """
                )
            )

    if "vehicle_locations" in tables and _has_column(inspector, "vehicle_locations", "geometry"):
        op.alter_column(
            "vehicle_locations",
            "geometry",
            existing_type=Geometry("POINT", srid=4326),
            type_=Geometry("POINTZ", srid=4326),
            postgresql_using="ST_Force3DZ(geometry)",
        )
        if "horizons" in tables and _has_column(inspector, "vehicle_locations", "horizon_id"):
            op.execute(
                sa.text(
                    """
                    UPDATE vehicle_locations AS vl
                    SET geometry = ST_SetSRID(
                        ST_MakePoint(
                            ST_X(vl.geometry),
                            ST_Y(vl.geometry),
                            h.height
                        ),
                        4326
                    )
                    FROM horizons AS h
                    WHERE h.id = vl.horizon_id
                      AND vl.geometry IS NOT NULL
                    """
                )
            )

    if "graph_edges" in tables and _has_column(inspector, "graph_edges", "geometry"):
        op.alter_column(
            "graph_edges",
            "geometry",
            existing_type=Geometry("LINESTRING", srid=4326),
            type_=Geometry("LINESTRINGZ", srid=4326),
            postgresql_using="ST_Force3DZ(geometry)",
        )
        if (
            "graph_nodes" in tables
            and _has_column(inspector, "graph_edges", "from_node_id")
            and _has_column(inspector, "graph_edges", "to_node_id")
            and _has_column(inspector, "graph_nodes", "geometry")
        ):
            op.execute(
                sa.text(
                    """
                    UPDATE graph_edges AS ge
                    SET geometry = ST_SetSRID(ST_MakeLine(fn.geometry, tn.geometry), 4326)
                    FROM graph_nodes AS fn, graph_nodes AS tn
                    WHERE fn.id = ge.from_node_id
                      AND tn.id = ge.to_node_id
                      AND ge.geometry IS NOT NULL
                    """
                )
            )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = set(inspector.get_table_names())

    if "graph_edges" in tables and _has_column(inspector, "graph_edges", "geometry"):
        op.alter_column(
            "graph_edges",
            "geometry",
            existing_type=Geometry("LINESTRINGZ", srid=4326),
            type_=Geometry("LINESTRING", srid=4326),
            postgresql_using="ST_Force2D(geometry)",
        )

    if "vehicle_locations" in tables and _has_column(inspector, "vehicle_locations", "geometry"):
        op.alter_column(
            "vehicle_locations",
            "geometry",
            existing_type=Geometry("POINTZ", srid=4326),
            type_=Geometry("POINT", srid=4326),
            postgresql_using="ST_Force2D(geometry)",
        )

    if "places" in tables and _has_column(inspector, "places", "geometry"):
        op.alter_column(
            "places",
            "geometry",
            existing_type=Geometry("POINTZ", srid=4326),
            type_=Geometry("POINT", srid=4326),
            postgresql_using="ST_Force2D(geometry)",
        )

    if "graph_nodes" in tables and _has_column(inspector, "graph_nodes", "geometry"):
        op.alter_column(
            "graph_nodes",
            "geometry",
            existing_type=Geometry("POINTZ", srid=4326),
            type_=Geometry("POINT", srid=4326),
            postgresql_using="ST_Force2D(geometry)",
        )
