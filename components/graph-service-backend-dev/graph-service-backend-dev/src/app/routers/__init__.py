"""API routes для graph-service."""

from app.routers.edges import edge_router
from app.routers.horizons import horizon_router
from app.routers.import_graphs import import_router
from app.routers.ladders import ladder_nodes_router, ladder_router
from app.routers.levels import levels_router
from app.routers.locations import location_router, route_router
from app.routers.nodes import node_router
from app.routers.places import place_router
from app.routers.sections import section_router
from app.routers.shafts import shaft_router
from app.routers.substrates import substrate_router
from app.routers.tags import tag_router
from app.routers.ws_vehicle_tracking import websocket_router

__all__ = [
    "edge_router",
    "horizon_router",
    "import_router",
    "ladder_nodes_router",
    "ladder_router",
    "levels_router",
    "location_router",
    "route_router",
    "node_router",
    "place_router",
    "section_router",
    "shaft_router",
    "substrate_router",
    "tag_router",
    "websocket_router",
]
