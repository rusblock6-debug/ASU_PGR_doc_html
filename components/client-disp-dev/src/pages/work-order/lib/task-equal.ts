import type { RouteTask } from '@/shared/api/endpoints/route-tasks';

import type { RouteTaskDraft, RouteTaskEditableField } from '../model/types';

/**
 * Сравнивает значение поля локальной задачи с серверной.
 * Используется для определения, изменилось ли поле относительно серверного значения.
 */
export function isFieldEqual(
  field: RouteTaskEditableField,
  localValue: RouteTaskDraft[RouteTaskEditableField],
  serverTask: RouteTask,
) {
  const fieldMap: Record<RouteTaskEditableField, keyof RouteTask> = {
    placeStartId: 'place_a_id',
    placeEndId: 'place_b_id',
    volume: 'volume',
    weight: 'weight',
    plannedTripsCount: 'planned_trips_count',
    message: 'message',
    taskType: 'type_task',
  };

  const serverValue = serverTask[fieldMap[field]] ?? null;
  const normalizedLocalValue = localValue ?? null;

  return normalizedLocalValue === serverValue;
}
