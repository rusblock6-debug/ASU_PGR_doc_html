import { createSelector } from '@reduxjs/toolkit';

import { EMPTY_ARRAY } from '@/shared/lib/constants';

import { ACTIVE_STATUS } from '../constants';
import { mergeVehicleTasks } from '../utils';

import { selectAllServerShiftTasks } from './shift-tasks';

/**
 * Серверные маршрутные задачи для конкретной машины.
 */
const selectServerTasksForVehicle = createSelector(
  [selectAllServerShiftTasks, (_state: RootState, vehicleId: number) => vehicleId],
  (serverShiftTasks, vehicleId) => {
    const shiftTask = serverShiftTasks.find((shifTask) => shifTask.vehicle_id === vehicleId);
    return shiftTask?.route_tasks ?? EMPTY_ARRAY;
  },
);

/**
 * Все маршрутные задания для конкретной машины объединённые с локальными изменениями.
 */
export const selectMergedVehicleTasks = createSelector(
  [
    selectServerTasksForVehicle,
    (state: RootState, vehicleId: number) => state.workOrder.created[vehicleId],
    (state: RootState, vehicleId: number) => state.workOrder.modified[vehicleId],
    (state: RootState, vehicleId: number) => state.workOrder.deleted[vehicleId],
  ],
  (serverTasks, created, modified, deleted) => mergeVehicleTasks(serverTasks, created, modified, deleted),
);

/**
 * Возвращает ID маршрутных заданий для конкретной машины.
 * Используется для маппинга списка — не триггерит перерисовку при изменении полей задания.
 */
export const selectMergedVehicleTaskIds = createSelector([selectMergedVehicleTasks], (tasks) =>
  tasks.map((task) => task.id),
);

/**
 * Количество маршрутных заданий для конкретной машины.
 */
export const selectVehicleTaskCount = createSelector([selectMergedVehicleTasks], (tasks) => tasks.length);

/**
 * Есть ли хотя бы одно задание с активным статусом («В работе») для конкретной машины.
 */
export const selectVehicleHasActiveTask = createSelector([selectMergedVehicleTasks], (tasks) =>
  tasks.some((t) => ACTIVE_STATUS.has(t.status)),
);

/**
 * Получить задание по taskId для машины.
 */
export const selectMergedVehicleTask = createSelector(
  [
    (state: RootState, vehicleId: number, _taskId: string) => selectMergedVehicleTasks(state, vehicleId),
    (_state: RootState, _vehicleId: number, taskId: string) => taskId,
  ],
  (tasks, taskId) => tasks.find((t) => t.id === taskId) ?? null,
);
