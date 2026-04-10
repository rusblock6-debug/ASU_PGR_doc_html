import type { RouteTaskResponse } from '@/shared/api/types/trip-service';

import { extractActiveRouteTaskIdFromPayload } from './parse-active-route-task-id';

const normalizeStatus = (s: string) => s.toUpperCase().replaceAll('-', '_');

/** Согласовано с entities/route-task isRouteTaskInProgress (без импорта shared→entities). */
const isRouteTaskInProgress = (status: string) => {
  const u = normalizeStatus(status);
  return u === 'ACTIVE' || u === 'IN_PROGRESS';
};

/**
 * Определяет маршрутное задание для главного экрана: сначала по ответу /active/task,
 * затем первое «в работе», иначе первое по списку.
 */
export const resolveActiveRouteTaskForMainScreen = (tasks: RouteTaskResponse[], activeTaskPayload: unknown) => {
  if (tasks.length === 0) {
    return null;
  }

  const fromApi = extractActiveRouteTaskIdFromPayload(activeTaskPayload);
  if (fromApi) {
    const match = tasks.find((t) => t.id === fromApi);
    if (match) {
      return match;
    }
  }

  const inProgress = tasks.find((t) => isRouteTaskInProgress(t.status));
  if (inProgress) {
    return inProgress;
  }

  return tasks[0] ?? null;
};
