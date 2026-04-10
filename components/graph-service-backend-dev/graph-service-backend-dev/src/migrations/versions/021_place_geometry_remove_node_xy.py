"""Place: remove location, add geometry; graph_nodes: remove x, y

Revision ID: 021
Revises: 020
Create Date: 2026-02-13

- У места (places): удалена колонка location (JSONB), добавлена геометрия (PostGIS POINT).
- У граф-ноды (graph_nodes): удалены колонки x, y (координаты берутся из geometry).
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from geoalchemy2 import Geometry
from loguru import logger

revision = "021"
down_revision = "020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    # --- places: location -> geometry ---
    if "places" in inspector.get_table_names():
        cols = {c["name"] for c in inspector.get_columns("places")}
        if "location" in cols and "geometry" not in cols:
            # Добавляем колонку geometry (сначала nullable для заполнения)
            op.add_column(
                "places",
                sa.Column(
                    "geometry",
                    Geometry(geometry_type="POINT", srid=4326),
                    nullable=True,
                ),
            )
            # Переносим данные: location JSONB { "x": float, "y": float } -> POINT(x, y)
            # Поддержка и x/y (система координат), и lat/lng (WGS84)
            conn.execute(
                sa.text("""
                UPDATE places
                SET geometry = ST_SetSRID(
                    ST_MakePoint(
                        COALESCE((location->>'x')::double precision, (location->>'lng')::double precision, 0),
                        COALESCE((location->>'y')::double precision, (location->>'lat')::double precision, 0)
                    ),
                    4326
                )
                WHERE location IS NOT NULL
                """)
            )
            conn.execute(
                sa.text("""
                UPDATE places
                SET geometry = ST_SetSRID(ST_MakePoint(0::double precision, 0::double precision), 4326)
                WHERE geometry IS NULL
                """)
            )
            op.alter_column(
                "places",
                "geometry",
                existing_type=Geometry(geometry_type="POINT", srid=4326),
                nullable=False,
            )
            op.drop_column("places", "location")
            # Проверяем существование индекса перед созданием
            indexes = inspector.get_indexes("places")
            index_names = {idx["name"] for idx in indexes}
            if "idx_places_geometry" not in index_names:
                op.execute(
                    sa.text("CREATE INDEX idx_places_geometry ON places USING GIST (geometry)")
                )
                logger.info("[OK] Created GIST index 'idx_places_geometry' on 'places'")
            else:
                logger.info("[SKIP] Index 'idx_places_geometry' already exists - skipping")
            logger.info("[OK] places: replaced 'location' with 'geometry'")
        elif "geometry" in cols:
            logger.info("[SKIP] places: 'geometry' already exists - skipping")
        else:
            logger.warning("[SKIP] places: 'location' not found - skipping")

    # --- graph_nodes: удаляем x, y ---
    if "graph_nodes" in inspector.get_table_names():
        nodes_cols = {c["name"] for c in inspector.get_columns("graph_nodes")}
        if "x" in nodes_cols or "y" in nodes_cols:
            with op.batch_alter_table("graph_nodes", schema=None) as batch_op:
                if "x" in nodes_cols:
                    batch_op.drop_column("x")
                if "y" in nodes_cols:
                    batch_op.drop_column("y")
            logger.info("[OK] graph_nodes: dropped columns 'x', 'y'")
        else:
            logger.info("[SKIP] graph_nodes: columns 'x', 'y' already removed - skipping")


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    # --- graph_nodes: восстанавливаем x, y из geometry ---
    if "graph_nodes" in inspector.get_table_names():
        nodes_cols = {c["name"] for c in inspector.get_columns("graph_nodes")}
        if "x" not in nodes_cols and "y" not in nodes_cols:
            op.add_column(
                "graph_nodes",
                sa.Column("x", sa.Float(), nullable=True),
            )
            op.add_column(
                "graph_nodes",
                sa.Column("y", sa.Float(), nullable=True),
            )
            conn.execute(
                sa.text("""
                UPDATE graph_nodes SET x = ST_X(geometry), y = ST_Y(geometry)
                """)
            )
            op.alter_column(
                "graph_nodes",
                "x",
                existing_type=sa.Float(),
                nullable=False,
            )
            op.alter_column(
                "graph_nodes",
                "y",
                existing_type=sa.Float(),
                nullable=False,
            )
            logger.info("[OK] graph_nodes: restored columns 'x', 'y'")
        else:
            logger.info("[SKIP] graph_nodes: 'x' or 'y' already exist - skipping")

    # --- places: geometry -> location ---
    if "places" in inspector.get_table_names():
        cols = {c["name"] for c in inspector.get_columns("places")}
        if "geometry" in cols and "location" not in cols:
            op.execute(sa.text("DROP INDEX IF EXISTS idx_places_geometry"))
            op.add_column(
                "places",
                sa.Column(
                    "location",
                    postgresql.JSONB(astext_type=sa.Text()),
                    nullable=True,
                ),
            )
            conn.execute(
                sa.text("""
                UPDATE places
                SET location = jsonb_build_object(
                    'x', ST_X(geometry),
                    'y', ST_Y(geometry)
                )
                """)
            )
            op.alter_column(
                "places",
                "location",
                existing_type=postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
            )
            op.drop_column("places", "geometry")
            logger.info("[OK] places: replaced 'geometry' with 'location'")
        else:
            logger.info("[SKIP] places: 'geometry' not found or 'location' exists - skipping")
