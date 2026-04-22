/**
 * Извлекает число из объекта по списку ключей (первое валидное).
 */
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

const NEST_KEYS = ['payload', 'data', 'route', 'snapshot'] as const;

/**
 * Плоский слой: корень + вложенные объекты по типичным ключам.
 */
const flattenRecord = (root: unknown) => {
  if (!root || typeof root !== 'object' || Array.isArray(root)) {
    return {};
  }

  const base = root as Record<string, unknown>;
  const merged: Record<string, unknown> = { ...base };

  for (const key of NEST_KEYS) {
    const nested = base[key];
    if (nested && typeof nested === 'object' && !Array.isArray(nested)) {
      Object.assign(merged, nested as Record<string, unknown>);
    }
  }

  return merged;
};

/** Полный набор метрик маршрута после разбора payload (оба поля заданы). */
export interface RouteStreamMetrics {
  readonly distanceMeters: number;
  readonly durationSeconds: number;
}

/** Частичное обновление из одного SSE-сообщения (отсутствующие поля не трогаем в store). */
export interface RouteStreamPartialUpdate {
  distanceMeters?: number;
  durationSeconds?: number;
}

/**
 * Разбор payload SSE `/api/events/stream/routes`: метры до точки и время (секунды или минуты → секунды в store).
 * Ключи согласованы с типичными именами бэкенда; при смене контракта — расширить списки.
 */
export const parseRouteStreamPayload = (raw: unknown) => {
  const resolved: unknown = Array.isArray(raw) ? raw[0] : raw;
  const flat = flattenRecord(resolved);

  const distanceKeys = [
    'distance_meters',
    'distance_m',
    'distance_remaining_m',
    'meters_to_point',
    'remaining_meters',
    'distance_meters_remaining',
    'meters_remaining',
    'meters',
  ] as const;

  const durationKeys = [
    'duration_seconds',
    'eta_seconds',
    'time_seconds',
    'seconds_to_point',
    'time_to_point_sec',
    'eta_s',
    'seconds',
  ] as const;

  const out: RouteStreamPartialUpdate = {};

  const distanceMeters = pickFiniteNumber(flat, distanceKeys);
  if (distanceMeters !== null) {
    out.distanceMeters = distanceMeters;
  }

  const durationSeconds = pickFiniteNumber(flat, durationKeys);
  if (durationSeconds !== null) {
    out.durationSeconds = durationSeconds;
  }

  if (out.durationSeconds === undefined) {
    const minutesKeys = ['minutes_to_destination'] as const;
    const minutes = pickFiniteNumber(flat, minutesKeys);
    if (minutes !== null) {
      out.durationSeconds = minutes * 60;
    }
  }

  return out;
};
