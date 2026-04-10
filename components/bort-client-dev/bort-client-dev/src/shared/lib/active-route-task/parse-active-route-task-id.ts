const TOP_LEVEL_KEYS = ['task_id', 'route_task_id', 'id'] as const;

const NESTED_KEYS = ['route_task', 'data', 'payload', 'task'] as const;

const MAX_DEPTH = 6;

/**
 * Приводит значение к ID маршрутного задания (как в useRouteTaskActions.parseActiveTaskId).
 */
export const parsePrimitiveRouteTaskId = (raw: unknown) => {
  if (raw == null) {
    return null;
  }
  if (typeof raw === 'string') {
    const t = raw.trim();
    return t.length > 0 ? t : null;
  }
  if (typeof raw === 'number' || typeof raw === 'bigint') {
    return String(raw);
  }
  return null;
};

/**
 * Извлекает ID активного маршрутного задания из произвольного ответа GET /active/task.
 */
export const extractActiveRouteTaskIdFromPayload = (payload: unknown, depth = 0): string | null => {
  if (payload == null || depth > MAX_DEPTH) {
    return null;
  }

  if (typeof payload !== 'object') {
    return null;
  }

  const obj = payload as Record<string, unknown>;

  for (const key of TOP_LEVEL_KEYS) {
    const id = parsePrimitiveRouteTaskId(obj[key]);
    if (id) {
      return id;
    }
  }

  for (const key of NESTED_KEYS) {
    const nested = obj[key];
    if (nested != null && typeof nested === 'object') {
      const id = extractActiveRouteTaskIdFromPayload(nested, depth + 1);
      if (id) {
        return id;
      }
    }
  }

  return null;
};
