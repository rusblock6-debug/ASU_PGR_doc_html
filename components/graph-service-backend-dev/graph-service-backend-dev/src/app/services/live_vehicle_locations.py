"""In-memory cache of latest vehicle GPS from MQTT (same source as WebSocket vehicle-tracking).

Updated by MQTT when truck/+/sensor/gps/ds is received; read by route_progress_stream
so SSE uses the same fresh coordinates as the WS stream.
"""

from __future__ import annotations

import threading
from typing import Any

# vehicle_id (str) -> {"lat": float, "lon": float, "timestamp": float}
_cache: dict[str, dict[str, Any]] = {}
_lock = threading.Lock()


def update(vehicle_id: str, lat: float, lon: float, timestamp: float) -> None:
    """Store latest location for vehicle (call from MQTT handler)."""
    with _lock:
        _cache[vehicle_id] = {"lat": lat, "lon": lon, "timestamp": timestamp}


def get_for_vehicle_ids(vehicle_ids: set[int]) -> dict[int, dict[str, float]]:
    """Return latest lat/lon for each vehicle_id (int).

    Checks cache keys `str(id)` and `f"{id}_truck"`.
    """
    result: dict[int, dict[str, float]] = {}
    with _lock:
        for vid in vehicle_ids:
            for key in (str(vid), f"{vid}_truck"):
                if key in _cache:
                    entry = _cache[key]
                    result[vid] = {"lat": float(entry["lat"]), "lon": float(entry["lon"])}
                    break
    return result
