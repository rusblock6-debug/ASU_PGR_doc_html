"""API routes для graph-service."""

from fastapi import APIRouter

from app.routers import (
    edges,
    events_stream,
    horizons,
    import_graphs,
    levels,
    map_player,
    map_settings,
    nodes,
    places,
    sections,
    shafts,
    substrates,
    tags,
    vehicles,
)
from app.routers.ladders import ladder_nodes_router, ladder_router
from app.routers.locations import location_router, route_router

api_router = APIRouter(prefix="/api")

api_router.include_router(horizons.router)
api_router.include_router(levels.router)
api_router.include_router(nodes.router)
api_router.include_router(edges.router)
api_router.include_router(tags.router)
api_router.include_router(places.router)
api_router.include_router(ladder_router)
api_router.include_router(sections.router)
api_router.include_router(import_graphs.router)
api_router.include_router(substrates.router)
api_router.include_router(shafts.router)
api_router.include_router(map_settings.router)
api_router.include_router(location_router)
api_router.include_router(route_router)
api_router.include_router(events_stream.router)
api_router.include_router(vehicles.router)
api_router.include_router(ladder_nodes_router)
api_router.include_router(map_player.router)

__all__ = [
    "api_router",
]
