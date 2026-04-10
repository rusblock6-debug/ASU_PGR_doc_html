import { RouteStatus } from '@/shared/api/endpoints/route-tasks';
import type { RouteTaskUpsertItem } from '@/shared/api/endpoints/route-tasks';
import type { ShiftTask, ShiftTaskBulkUpsertItem } from '@/shared/api/endpoints/shift-tasks';
import { assertHasValue } from '@/shared/lib/assert-has-value';
import { hasValue } from '@/shared/lib/has-value';

import type { CurrentShift, RouteTaskEditableFields, WorkOrderEdits } from '../types';

/**
 * Формирует данные для отправки в API.
 */
export function buildApiItems(
  validVehicleIds: readonly number[],
  edits: WorkOrderEdits,
  serverShiftTasks: readonly ShiftTask[],
  currentShift: CurrentShift,
) {
  const { created, modified, deleted } = edits;
  const shiftTaskMap = new Map(serverShiftTasks.map((shiftTask) => [shiftTask.vehicle_id, shiftTask]));

  const items: ShiftTaskBulkUpsertItem[] = [];

  for (const vehicleId of validVehicleIds) {
    const existingShiftTask = shiftTaskMap.get(vehicleId);
    const serverRouteTasks = existingShiftTask?.route_tasks ?? [];

    const vehicleCreated = created[vehicleId] ?? {};
    const vehicleModified = modified[vehicleId] ?? {};
    const vehicleDeleted = new Set(deleted[vehicleId] ?? []);

    // Существующие задачи (исключает удаленные задания, добавляет задания в которых редактировали поля)
    const existingTasks = serverRouteTasks
      .filter((task) => !vehicleDeleted.has(task.id))
      .map((task) => mapServerTaskToUpsertItem(task, vehicleModified[task.id]));

    // Новые задачи для машины
    const newTasks: RouteTaskUpsertItem[] = Object.values(vehicleCreated).map((task) => {
      assertHasValue(task.placeStartId, `Не указано место погрузки (транспорт ${vehicleId})`);
      assertHasValue(task.placeEndId, `Не указано место разгрузки (транспорт ${vehicleId})`);
      assertHasValue(task.plannedTripsCount, `Не указаны рейсы (транспорт ${vehicleId})`);

      return {
        shift_task_id: existingShiftTask?.id ?? null,
        route_order: 0, // будет перезаписан при финальной сборке
        place_a_id: task.placeStartId,
        place_b_id: task.placeEndId,
        type_task: task.taskType,
        planned_trips_count: task.plannedTripsCount,
        volume: task.volume,
        weight: task.weight,
        message: task.message,
        status: task.status === RouteStatus.EMPTY ? RouteStatus.SENT : task.status,
      };
    });

    // Объединяем и фильтруем только заполненные
    const allTasks = [...existingTasks, ...newTasks].filter(isTaskFilled);

    items.push({
      id: existingShiftTask?.id,
      vehicle_id: vehicleId,
      work_regime_id: currentShift.workRegimeId,
      shift_date: currentShift.shiftDate,
      shift_num: currentShift.shiftNum,
      route_tasks: allTasks.map((task, index) => ({
        id: task.id,
        route_order: index,
        shift_task_id: hasValue(existingShiftTask?.id) ? existingShiftTask?.id : null,
        place_a_id: task.place_a_id,
        place_b_id: task.place_b_id,
        type_task: task.type_task,
        planned_trips_count: task.planned_trips_count,
        volume: task.volume,
        weight: task.weight,
        message: task.message,
        status: task.status,
      })),
    });
  }

  return { items };
}

/**
 * Применяет изменения для существующей задачи.
 */
function mapServerTaskToUpsertItem(
  serverTask: ShiftTask['route_tasks'][number],
  patch?: Partial<RouteTaskEditableFields>,
): RouteTaskUpsertItem {
  return {
    id: serverTask.id,
    shift_task_id: serverTask.shift_task_id,
    route_order: serverTask.route_order,
    place_a_id: patch?.placeStartId ?? serverTask.place_a_id,
    place_b_id: patch?.placeEndId ?? serverTask.place_b_id,
    type_task: patch?.taskType ?? serverTask.type_task,
    planned_trips_count: patch?.plannedTripsCount ?? serverTask.planned_trips_count,
    volume: patch?.volume ?? serverTask.volume,
    weight: patch?.weight ?? serverTask.weight,
    message: patch?.message ?? serverTask.message,
    status: serverTask.status,
  };
}

/**
 * Проверяет заполненность задачи.
 */
function isTaskFilled(task: RouteTaskUpsertItem) {
  return hasValue(task.place_a_id) && hasValue(task.place_b_id) && hasValue(task.volume);
}
