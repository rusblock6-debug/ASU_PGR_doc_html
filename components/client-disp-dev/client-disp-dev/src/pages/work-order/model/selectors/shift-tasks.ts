import { createSelector } from '@reduxjs/toolkit';

import { type ShiftTask, type ShiftTasksQueryArg, shiftTaskRtkApi } from '@/shared/api/endpoints/shift-tasks';
import { EMPTY_ARRAY } from '@/shared/lib/constants';

import { STATUS_FILTER_MAP } from '../constants';

import { selectFilteredVehicleIds, selectSelectedStatus, selectShiftTasksQueryArg } from './base';

/**
 * Кэш селекторов RTK Query по ключу смены.
 * Нужно чтобы не создавать новый селектор при каждом вызове.
 */
const shiftTasksQuerySelectors = new Map<string, ReturnType<typeof shiftTaskRtkApi.endpoints.getShiftTasks.select>>();

/**
 * Получить или создать кэшированный селектор для RTK Query.
 */
const getShiftTasksQuerySelector = (queryArg: ShiftTasksQueryArg) => {
  const key = JSON.stringify(queryArg);
  let selector = shiftTasksQuerySelectors.get(key);

  if (!selector) {
    selector = shiftTaskRtkApi.endpoints.getShiftTasks.select(queryArg);
    shiftTasksQuerySelectors.set(key, selector);
  }

  return selector;
};

/**
 * Данные наряд-задания из кэша RTK Query.
 */
const selectShiftTasksData = (state: RootState) => {
  const queryArg = selectShiftTasksQueryArg(state);
  return getShiftTasksQuerySelector(queryArg)(state).data;
};

/**
 * Все наряд-задания из кэша RTK Query.
 */
export const selectAllServerShiftTasks = createSelector([selectShiftTasksData], (data): readonly ShiftTask[] => {
  return data?.pages.flatMap((page: { items: readonly ShiftTask[] }) => page.items) ?? EMPTY_ARRAY;
});

/**
 * ID машин для отображения с учётом фильтра по статусу.
 * При активном фильтре — только машины, у которых есть route_tasks с подходящим статусом.
 */
export const selectDisplayedVehicleIds = createSelector(
  [selectFilteredVehicleIds, selectSelectedStatus, selectAllServerShiftTasks],
  (vehicleIds, selectedStatus, serverShiftTasks) => {
    if (selectedStatus === 'all') return vehicleIds;

    const statusFilter = STATUS_FILTER_MAP[selectedStatus];
    const taskVehicleIds = new Set(
      serverShiftTasks
        .filter((task) => task.route_tasks.some((routeTask) => statusFilter?.includes(routeTask.status)))
        .map((task) => task.vehicle_id),
    );

    return vehicleIds.filter((id) => taskVehicleIds.has(id));
  },
);

/**
 * Получить маршрутную задачу по ID из RTK Query кэша.
 */
export const selectServerTaskById = createSelector(
  [selectAllServerShiftTasks, (_state: RootState, taskId: string) => taskId],
  (allServerTasks, taskId) => {
    for (const shiftTask of allServerTasks) {
      const routeTask = shiftTask.route_tasks.find((task) => task.id === taskId);
      if (routeTask) return routeTask;
    }

    return null;
  },
);

/**
 * Есть ли хотя бы одно задание, которое было сохранено на сервере.
 */
export const selectHasSavedTask = createSelector([selectAllServerShiftTasks], (serverShiftTasks) => {
  return serverShiftTasks.some((shiftTask) => shiftTask.route_tasks.length > 0);
});
