"""Сопоставление place_id → graph node_id для маршрутов (как в live route stream)."""

from __future__ import annotations

from geoalchemy2.functions import ST_X, ST_Y
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import Place
from app.services.locations import loc_finder


async def get_primary_node_id_per_place(db: AsyncSession, place_ids: set[int]) -> dict[int, int]:
    """Первый node_id по place_id с fallback на ближайший узел.

    Берется минимальный node_id для каждого place_id (order_by place_id, node_id).
    """
    if not place_ids:
        return {}

    query = (
        select(Place.id, Place.node_id)
        .where(
            Place.id.in_(sorted(place_ids)),
            Place.node_id.isnot(None),
        )
        .order_by(Place.id, Place.node_id)
    )
    rows = (await db.execute(query)).all()

    place_node_map: dict[int, int] = {}
    for place_id, node_id in rows:
        place_node_map.setdefault(int(place_id), int(node_id))

    missing = place_ids - set(place_node_map)
    if missing:
        res = await db.execute(
            select(
                Place.id,
                ST_Y(Place.geometry).label("lat"),
                ST_X(Place.geometry).label("lon"),
            ).where(Place.id.in_(sorted(missing))),
        )
        for place_id, lat, lon in res.all() or []:
            if lat is None or lon is None:
                continue
            try:
                node_id = await loc_finder.find_nearest_node_to_bort(
                    float(lat),
                    float(lon),
                    db,
                )
                place_node_map[int(place_id)] = node_id
            except Exception:
                logger.warning(
                    "place_route_nodes: failed to find nearest node for place_id=%s",
                    place_id,
                    exc_info=True,
                )

    return place_node_map
