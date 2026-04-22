from __future__ import annotations

import json

import pytest
from geoalchemy2.shape import from_shape
from shapely.geometry import LineString, Point
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.enum.places import PlaceTypeEnum
from app.models.database import AuditOutbox, GraphEdge, GraphNode, Place, VehicleLocation

pytestmark = pytest.mark.integration


def _point_wkb(x: float = 37.6, y: float = 55.7, z: float = 0.0, srid: int = 4326):
    return from_shape(Point(x, y, z), srid=srid)


def _linestring_wkb(
    coords: list[tuple[float, float, float]] | None = None,
    srid: int = 4326,
):
    coords = coords or [(37.6, 55.7, 0.0), (37.7, 55.8, 0.0)]
    return from_shape(LineString(coords), srid=srid)


async def _last_audit_row(session: AsyncSession, entity_type: str):
    stmt = (
        select(AuditOutbox)
        .where(AuditOutbox.entity_type == entity_type)
        .order_by(AuditOutbox.timestamp.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    row = result.scalar_one()
    return row


async def _create_horizon(session: AsyncSession, name: str = "test-horizon") -> int:
    result = await session.execute(
        text(
            "INSERT INTO horizons (name, height) VALUES (:name, :height) RETURNING id",
        ),
        {"name": name, "height": 100.0},
    )
    horizon_id = result.scalar_one()
    await session.flush()
    return horizon_id


async def test_graph_node_audit_serializes_geometry(async_session: AsyncSession):
    horizon_id = await _create_horizon(async_session, "node-horizon")

    node = GraphNode(
        horizon_id=horizon_id,
        node_type="road",
        geometry=_point_wkb(37.6, 55.7),
    )
    async_session.add(node)
    await async_session.flush()

    audit = await _last_audit_row(async_session, "graph_nodes")
    assert audit.operation == "create"

    new_vals = audit.new_values
    geom_val = new_vals["geometry"]
    assert isinstance(geom_val, str)
    assert "POINT" in geom_val
    assert "37.6" in geom_val
    assert "55.7" in geom_val

    json.dumps(new_vals)


async def test_graph_edge_audit_serializes_linestring(async_session: AsyncSession):
    horizon_id = await _create_horizon(async_session, "edge-horizon")

    node_a = GraphNode(
        horizon_id=horizon_id,
        node_type="road",
        geometry=_point_wkb(37.6, 55.7),
    )
    node_b = GraphNode(
        horizon_id=horizon_id,
        node_type="road",
        geometry=_point_wkb(37.7, 55.8),
    )
    async_session.add_all([node_a, node_b])
    await async_session.flush()

    edge = GraphEdge(
        horizon_id=horizon_id,
        from_node_id=node_a.id,
        to_node_id=node_b.id,
        edge_type="horizontal",
        geometry=_linestring_wkb([(37.6, 55.7, 0.0), (37.7, 55.8, 0.0)]),
    )
    async_session.add(edge)
    await async_session.flush()

    audit = await _last_audit_row(async_session, "graph_edges")
    geom_val = audit.new_values["geometry"]
    assert isinstance(geom_val, str)
    assert "LINESTRING" in geom_val

    json.dumps(audit.new_values)


async def test_place_audit_serializes_geometry(async_session: AsyncSession):
    horizon_id = await _create_horizon(async_session, "place-horizon")

    node = GraphNode(
        horizon_id=horizon_id,
        node_type="road",
        geometry=_point_wkb(38.0, 56.0),
    )
    async_session.add(node)
    await async_session.flush()

    place = Place(
        name="test-place-audit",
        type=PlaceTypeEnum.park,
        node_id=node.id,
    )
    async_session.add(place)
    await async_session.flush()

    audit = await _last_audit_row(async_session, "places")
    new_vals = audit.new_values
    assert new_vals["node_id"] == node.id

    json.dumps(new_vals)


async def test_vehicle_location_audit_serializes_geometry(async_session: AsyncSession):
    vl = VehicleLocation(
        vehicle_id="truck-01",
        geometry=_point_wkb(39.0, 57.0),
    )
    async_session.add(vl)
    await async_session.flush()

    audit = await _last_audit_row(async_session, "vehicle_locations")
    geom_val = audit.new_values["geometry"]
    assert isinstance(geom_val, str)
    assert "POINT" in geom_val

    json.dumps(audit.new_values)


async def test_node_update_audit_serializes_old_and_new_geometry(async_session: AsyncSession):
    horizon_id = await _create_horizon(async_session, "upd-horizon")

    node = GraphNode(
        horizon_id=horizon_id,
        node_type="road",
        geometry=_point_wkb(37.6, 55.7),
    )
    async_session.add(node)
    await async_session.commit()

    node.geometry = _point_wkb(38.0, 56.0)
    await async_session.commit()

    audit = await _last_audit_row(async_session, "graph_nodes")
    assert audit.operation == "update"

    old_geom = audit.old_values["geometry"]
    new_geom = audit.new_values["geometry"]
    assert isinstance(old_geom, str)
    assert isinstance(new_geom, str)
    assert "37.6" in old_geom
    assert "38" in new_geom

    json.dumps(audit.old_values)
    json.dumps(audit.new_values)


async def test_node_delete_audit_serializes_geometry(async_session: AsyncSession):
    horizon_id = await _create_horizon(async_session, "del-horizon")

    node = GraphNode(
        horizon_id=horizon_id,
        node_type="road",
        geometry=_point_wkb(37.6, 55.7),
    )
    async_session.add(node)
    await async_session.commit()

    await async_session.delete(node)
    await async_session.commit()

    audit = await _last_audit_row(async_session, "graph_nodes")
    assert audit.operation == "delete"

    old_geom = audit.old_values["geometry"]
    assert isinstance(old_geom, str)
    assert "POINT" in old_geom

    json.dumps(audit.old_values)
