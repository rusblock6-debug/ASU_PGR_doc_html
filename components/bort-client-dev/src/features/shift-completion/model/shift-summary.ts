import type { RouteTaskResponse } from '@/shared/api/endpoints/tasks';

/**
 * Агрегаты по маршрутам смены для экрана завершения.
 */
export const buildShiftSummary = (tasks: readonly RouteTaskResponse[]) => {
  let plannedTrips = 0;
  let actualTrips = 0;
  let volume = 0;
  let weight = 0;

  for (const t of tasks) {
    plannedTrips += t.planned_trips_count;
    actualTrips += t.actual_trips_count;
    volume += t.volume ?? 0;
    weight += t.weight ?? 0;
  }

  return {
    plannedTrips,
    actualTrips,
    volume,
    weight,
    routesCount: tasks.length,
  };
};
