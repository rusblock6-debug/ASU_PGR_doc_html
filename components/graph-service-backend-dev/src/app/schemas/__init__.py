"""Pydantic schemas для graph-service.
Собраны актуальные схемы без удалённых/устаревших модулей.
"""

# Common
from app.schemas.common import ErrorResponse, PaginationBase, TimestampBase

# Edges
from app.schemas.edges import EdgeBase, EdgeCreate, EdgeResponse

# Graph Data
from app.schemas.graph_datas import GraphData

# Horizons
from app.schemas.horizons import (
    HorizonBase,
    HorizonCreate,
    HorizonListResponse,
    HorizonResponse,
    HorizonUpdate,
)

# Import Schemas
from app.schemas.import_graphs import (
    ImportEdge,
    ImportGraphData,
    ImportGraphRequest,
    ImportHorizon,
    ImportNode,
    ImportResultResponse,
    ImportTag,
)

# Ladders
from app.schemas.ladders import (
    LadderBase,
    LadderCreate,
    LadderListResponse,
    LadderResponse,
    LadderUpdate,
)

# Locations
from app.schemas.locations import LocationRequest, LocationResponse

# Nodes
from app.schemas.nodes import NodeBase, NodeCreate, NodeResponse

# Places
from app.schemas.places import PlaceCreate, PlacePatch, PlaceResponse, PlaceUpdate

# Locations
# Nodes
# Places
# Shafts
from app.schemas.shafts import (
    ShaftBase,
    ShaftBulkCreateRequest,
    ShaftBulkUpdateRequest,
    ShaftCreate,
    ShaftListResponse,
    ShaftResponse,
    ShaftShort,
    ShaftUpdateBulk,
    ShaftUpdateSingle,
)

# Substrates
from app.schemas.substrates import (
    SubstrateCreate,
    SubstrateListResponse,
    SubstrateResponse,
    SubstrateWithSvgResponse,
)

# Edges
# Graph Data
# Tags
from app.schemas.tags import (
    APITagBaseModel,
    APITagCreateModel,
    APITagResponseModel,
    APITagsResponseModel,
    APITagUpdateModel,
)

# Tags

__all__ = [
    # Common
    "TimestampBase",
    "PaginationBase",
    "ErrorResponse",
    # Shafts
    "ShaftBase",
    "ShaftCreate",
    "ShaftUpdateSingle",
    "ShaftUpdateBulk",
    "ShaftShort",
    "ShaftResponse",
    "ShaftListResponse",
    "ShaftBulkCreateRequest",
    "ShaftBulkUpdateRequest",
    # Horizons
    "HorizonBase",
    "HorizonCreate",
    "HorizonUpdate",
    "HorizonResponse",
    "HorizonListResponse",
    # Nodes
    "NodeBase",
    "NodeCreate",
    "NodeResponse",
    # Ladders
    "LadderBase",
    "LadderCreate",
    "LadderUpdate",
    "LadderResponse",
    "LadderListResponse",
    # Edges
    "EdgeBase",
    "EdgeCreate",
    "EdgeResponse",
    # Graph Data
    "GraphData",
    # Tags
    "APITagBaseModel",
    "APITagCreateModel",
    "APITagResponseModel",
    "APITagUpdateModel",
    "APITagsResponseModel",
    # Locations
    "LocationRequest",
    "LocationResponse",
    # Places
    "PlaceCreate",
    "PlacePatch",
    "PlaceUpdate",
    "PlaceResponse",
    # Import Schemas
    "ImportNode",
    "ImportEdge",
    "ImportTag",
    "ImportHorizon",
    "ImportGraphRequest",
    "ImportGraphData",
    "ImportResultResponse",
    # Substrates
    "SubstrateCreate",
    "SubstrateResponse",
    "SubstrateListResponse",
    "SubstrateWithSvgResponse",
]
