"""SSE stream for vehicle state (status, horizon, last place/tag)."""

from __future__ import annotations

import asyncio
import json
import re
from collections.abc import AsyncGenerator
from typing import Any

from fastapi import Request
from loguru import logger

from app.core.redis.vehicle import PLACES_SUFFIX, REDIS_KEY_PREFIX, STATE_SUFFIX
from app.core.redis.vehicle.vehicle_places import get_all_vehicle_places
from app.core.redis.vehicle.vehicle_state import get_all_vehicle_states
from app.schemas.vehicles import VehicleStateEvent

_VID_PATTERN = re.compile(
    rf"^{re.escape(REDIS_KEY_PREFIX)}(\d+)(?:{re.escape(PLACES_SUFFIX)}|{re.escape(STATE_SUFFIX)})$",
)


def _extract_vehicle_id(redis_key: str) -> int | None:
    m = _VID_PATTERN.match(redis_key)
    return int(m.group(1)) if m else None


VehicleSnapshot = dict[int, tuple[str | None, Any, Any]]


def _build_snapshot() -> VehicleSnapshot:
    """Read Redis and return {vehicle_id: (state, horizon, place_id)}."""
    all_places = get_all_vehicle_places()
    all_states = get_all_vehicle_states()

    vehicle_ids: set[int] = set()
    places_by_vid: dict[int, dict[str, Any]] = {}
    state_by_vid: dict[int, str] = {}

    for key, data in all_places.items():
        vid = _extract_vehicle_id(key)
        if vid is not None:
            vehicle_ids.add(vid)
            places_by_vid[vid] = data

    for key, state_val in all_states.items():
        vid = _extract_vehicle_id(key)
        if vid is not None:
            vehicle_ids.add(vid)
            state_by_vid[vid] = state_val

    snapshot: VehicleSnapshot = {}
    for vid in vehicle_ids:
        place_data = places_by_vid.get(vid, {})
        place_id = place_data.get("place_id")
        horizon = place_data.get("horizon")
        state = state_by_vid.get(vid)

        if place_id is not None:
            try:
                place_id = int(place_id)
            except (TypeError, ValueError):
                place_id = None
        if horizon is not None:
            try:
                horizon = int(horizon)
            except (TypeError, ValueError):
                horizon = None

        snapshot[vid] = (state, horizon, place_id)

    return snapshot


def _make_event(vid: int, state: str | None, horizon: Any, place_id: Any) -> dict[str, Any]:
    return VehicleStateEvent(
        event_type="vehicle_state",
        vehicle_id=vid,
        state=state,
        horizon_id=horizon,
        place_id=place_id,
    ).model_dump()


def _snapshot_to_items(snapshot: VehicleSnapshot) -> list[dict[str, Any]]:
    return [
        _make_event(vid, state, horizon, place_id)
        for vid, (state, horizon, place_id) in sorted(snapshot.items())
    ]


def _diff_items(
    prev: VehicleSnapshot,
    curr: VehicleSnapshot,
) -> list[dict[str, Any]]:
    changed: list[dict[str, Any]] = []
    for vid, cur_tuple in curr.items():
        if prev.get(vid) != cur_tuple:
            state, horizon, place_id = cur_tuple
            changed.append(_make_event(vid, state, horizon, place_id))
    return changed


async def vehicle_state_stream(request: Request) -> AsyncGenerator[str]:
    """SSE generator: polls Redis ~1s, emits diff of vehicle state."""
    logger.info("SSE vehicle stream client connected")

    try:
        yield f"data: {json.dumps({'type': 'connected', 'stream': 'vehicle'})}\n\n"
    except Exception as exc:
        logger.error("SSE vehicle stream: failed to send connected event", error=str(exc))
        yield f"data: {json.dumps({'type': 'error', 'message': str(exc)})}\n\n"
        return

    prev_snapshot: VehicleSnapshot = {}

    try:
        while True:
            try:
                if await request.is_disconnected():
                    logger.info("SSE vehicle stream client disconnected")
                    break
            except Exception as exc:
                logger.warning("SSE vehicle stream: is_disconnected check failed", error=str(exc))
                break

            try:
                snapshot = _build_snapshot()

                if not prev_snapshot:
                    items = _snapshot_to_items(snapshot)
                else:
                    items = _diff_items(prev_snapshot, snapshot)

                prev_snapshot = snapshot

                if items:
                    yield f"data: {json.dumps(items)}\n\n"
                else:
                    yield ": heartbeat\n\n"
            except Exception as exc:
                logger.error("Vehicle stream SSE iteration failed", error=str(exc))
                yield ": heartbeat\n\n"

            await asyncio.sleep(1)
    finally:
        logger.info("SSE vehicle stream connection closed")
