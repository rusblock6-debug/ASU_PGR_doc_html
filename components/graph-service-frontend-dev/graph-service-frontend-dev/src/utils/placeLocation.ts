import { GeoJSONPoint, Place } from '../types/graph';

export type LonLat = { lon: number; lat: number };
export type XY = { x: number; y: number };

function isFiniteNumber(v: unknown): v is number {
  return typeof v === 'number' && Number.isFinite(v);
}

function isGeoJSONPoint(v: unknown): v is GeoJSONPoint {
  if (!v || typeof v !== 'object') return false;
  const obj = v as any;
  return obj.type === 'Point' && Array.isArray(obj.coordinates);
}

/**
 * Normalizes Place.location into {lon,lat}.
 * - Supports legacy `{x,y}` (treated as `{lon,lat}`) and GeoJSON Point.
 * - Returns null if coordinates are missing/invalid.
 */
export function getPlaceLonLat(place: Pick<Place, 'location'>): LonLat | null {
  const loc: any = place.location;
  if (!loc) return null;

  // legacy {x,y}
  if (isFiniteNumber(loc.x) && isFiniteNumber(loc.y)) {
    return { lon: loc.x, lat: loc.y };
  }

  // sometimes backend still returns {lat,lon}
  if (isFiniteNumber(loc.lon) && isFiniteNumber(loc.lat)) {
    return { lon: loc.lon, lat: loc.lat };
  }

  // GeoJSON Point: coordinates [lon, lat]
  if (isGeoJSONPoint(loc)) {
    const coords = loc.coordinates;
    const lon = coords?.[0];
    const lat = coords?.[1];
    if (isFiniteNumber(lon) && isFiniteNumber(lat)) {
      return { lon, lat };
    }
  }

  return null;
}

/**
 * Map coordinates for places (canvas x,y).
 * Supports: place.location.x/y (canvas), GeoJSON Point.
 * Does NOT convert GPS — use getPlaceCanvasXY for API responses with location.lat/lon.
 */
export function getPlaceMapXY(place: Pick<Place, 'location'>): XY | null {
  const loc: any = place.location;
  if (!loc) return null;

  if (isFiniteNumber(loc.x) && isFiniteNumber(loc.y)) {
    return { x: loc.x, y: loc.y };
  }
  if (isGeoJSONPoint(loc)) {
    const coords = loc.coordinates;
    const x = coords?.[0];
    const y = coords?.[1];
    if (isFiniteNumber(x) && isFiniteNumber(y)) return { x, y };
  }
  return null;
}

export type TransformGPStoCanvas = (lat: number, lon: number) => { x: number; y: number };

/**
 * Returns canvas coordinates for a place. Uses getPlaceMapXY (canvas/GeoJSON);
 * if backend sent only location.lat/lon (GPS), converts via transformGPStoCanvas.
 */
export function getPlaceCanvasXY(
  place: Pick<Place, 'location'>,
  transformGPStoCanvas: TransformGPStoCanvas
): XY | null {
  const xy = getPlaceMapXY(place);
  if (xy) return xy;
  const ll = getPlaceLonLat(place);
  if (ll) return transformGPStoCanvas(ll.lat, ll.lon);
  return null;
}



