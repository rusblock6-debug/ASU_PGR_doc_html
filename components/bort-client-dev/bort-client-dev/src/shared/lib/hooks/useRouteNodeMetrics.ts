import { useGetPlaceQuery } from '@/shared/api/endpoints/places';
import { useGetRouteBetweenNodesQuery, useGetRouteProgressQuery } from '@/shared/api/endpoints/routes';
import { NO_DATA } from '@/shared/lib/constants';
import { getRouteStreamDistanceKmParts, getRouteStreamDurationMinutesCeilParts } from '@/shared/lib/route-stream';

/** Первое конечное число по списку ключей объекта (число или строка с запятой как десятичным разделителем). */
const pickFiniteNumber = (record: Record<string, unknown>, keys: readonly string[]) => {
  for (const key of keys) {
    const raw = record[key];
    if (typeof raw === 'number' && Number.isFinite(raw)) {
      return raw;
    }
    if (typeof raw === 'string') {
      const parsed = Number.parseFloat(raw.replace(',', '.'));
      if (Number.isFinite(parsed)) {
        return parsed;
      }
    }
  }
  return null;
};

/** Метры полного маршрута из ответа GET /api/route/{a}/{b}. */
const extractRouteDistanceMeters = (raw: unknown) => {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) {
    return null;
  }
  const flat = raw as Record<string, unknown>;
  const m = pickFiniteNumber(flat, [
    'distance_meters',
    'distance_m',
    'meters',
    'length_meters',
    'total_distance_m',
    'route_length_m',
    'total_length_m',
    'distance_remaining_m',
  ]);
  if (m !== null) {
    return m;
  }
  const km = pickFiniteNumber(flat, ['distance_km', 'distanceKm', 'length_km']);
  if (km !== null) {
    return km * 1000;
  }
  return null;
};

/** Секунды времени в пути из ответа GET /api/route/progress/... */
const extractRouteDurationSeconds = (raw: unknown) => {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) {
    return null;
  }
  const flat = raw as Record<string, unknown>;
  const timeData = flat['time_data'];
  if (timeData && typeof timeData === 'object' && !Array.isArray(timeData)) {
    const td = timeData as Record<string, unknown>;
    const nested = pickFiniteNumber(td, ['total_seconds', 'seconds', 'duration_seconds', 'eta_seconds']);
    if (nested !== null) {
      return nested;
    }
  }
  const sec = pickFiniteNumber(flat, [
    'duration_seconds',
    'eta_seconds',
    'time_seconds',
    'seconds',
    'travel_time_seconds',
    'time_to_point_sec',
  ]);
  if (sec !== null) {
    return sec;
  }
  const min = pickFiniteNumber(flat, ['duration_minutes', 'minutes', 'minutes_to_destination', 'eta_minutes']);
  if (min !== null) {
    return min * 60;
  }
  return null;
};

/** Подписи «~N км» и «~M мин» для UI или «—», если метрики нет. */
const formatTildeKmMin = (meters: number | null, seconds: number | null) => {
  const distParts = getRouteStreamDistanceKmParts(meters);
  const durParts = getRouteStreamDurationMinutesCeilParts(seconds);
  return {
    distanceLabel: distParts ? `~${distParts.value} ${distParts.unit}` : NO_DATA.LONG_DASH,
    durationLabel: durParts ? `~${durParts.value} ${durParts.unit}` : NO_DATA.LONG_DASH,
  };
};

/** Долгота из объекта локации (lon или lng). */
const readLon = (loc: { lon?: number; lng?: number; lat?: number } | null | undefined) => {
  if (!loc || typeof loc !== 'object') {
    return null;
  }
  const lon = loc.lon ?? loc.lng;
  return typeof lon === 'number' && Number.isFinite(lon) ? lon : null;
};

/** Широта из объекта локации. */
const readLat = (loc: { lat?: number } | null | undefined) => {
  if (!loc || typeof loc !== 'object') {
    return null;
  }
  const lat = loc.lat;
  return typeof lat === 'number' && Number.isFinite(lat) ? lat : null;
};

/** Расстояние и время в пути по place_a_id / place_b_id (graph: places → route + route/progress). */
export const useRouteNodeMetrics = (placeAId: number, placeBId: number) => {
  const { data: placeA, isLoading: isLoadingA } = useGetPlaceQuery(placeAId, { skip: !placeAId });
  const { data: placeB, isLoading: isLoadingB } = useGetPlaceQuery(placeBId, { skip: !placeBId });

  const startNodeId = placeA?.node_id ?? null;
  const targetNodeId = placeB?.node_id ?? null;
  const hasNodes =
    startNodeId != null && targetNodeId != null && Number.isFinite(startNodeId) && Number.isFinite(targetNodeId);

  const loc = placeA?.location;
  const lat = readLat(loc);
  const lon = readLon(loc);
  const hasProgressCoords = lat != null && lon != null;

  const skipRoute = !hasNodes;
  const skipProgress = skipRoute || !hasProgressCoords;

  const { data: routeBetween, isLoading: isLoadingBetween } = useGetRouteBetweenNodesQuery(
    { startNodeId: startNodeId ?? 0, targetNodeId: targetNodeId ?? 0 },
    { skip: skipRoute },
  );

  const { data: routeProgress, isLoading: isLoadingProgress } = useGetRouteProgressQuery(
    { startNodeId: startNodeId ?? 0, targetNodeId: targetNodeId ?? 0, lat: lat ?? 0, lon: lon ?? 0 },
    { skip: skipProgress },
  );

  const meters = extractRouteDistanceMeters(routeBetween) ?? extractRouteDistanceMeters(routeProgress);
  const seconds = extractRouteDurationSeconds(routeProgress);
  const { distanceLabel, durationLabel } = formatTildeKmMin(meters, seconds);

  const isLoading =
    isLoadingA || isLoadingB || (!skipRoute && isLoadingBetween) || (!skipProgress && isLoadingProgress);

  return { distanceLabel, durationLabel, distanceMeters: meters, durationSeconds: seconds, isLoading };
};
