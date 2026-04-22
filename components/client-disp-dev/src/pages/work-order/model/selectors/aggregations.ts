import { createSelector } from '@reduxjs/toolkit';

import { loadTypesRtkApi } from '@/shared/api/endpoints/load-types';
import { placeRtkApi } from '@/shared/api/endpoints/places';
import { RouteStatus, type RouteTaskStatus } from '@/shared/api/endpoints/route-tasks';
import { hasValue } from '@/shared/lib/has-value';

import { selectMergedVehicleTask, selectMergedVehicleTasks } from './merged-tasks';
import { selectAllServerShiftTasks } from './shift-tasks';

const EXCLUDED_TOTAL_STATUSES: ReadonlySet<RouteTaskStatus> = new Set([RouteStatus.SENT, RouteStatus.REJECTED]);

/**
 * Общий объём по всему транспорту.
 */
export const selectTotalVolume = createSelector(
  [
    selectAllServerShiftTasks,
    (state: RootState) => state.workOrder.created,
    (state: RootState) => state.workOrder.modified,
    (state: RootState) => state.workOrder.deleted,
  ],
  (serverShiftTasks, created, modified, deleted) => {
    const deletedSet = new Set(Object.values(deleted).flat());

    const serverTotal = serverShiftTasks
      .flatMap((st) => {
        const vehicleId = st.vehicle_id;
        const vehicleModified = modified[vehicleId] ?? {};

        return st.route_tasks
          .filter((task) => !deletedSet.has(task.id) && !EXCLUDED_TOTAL_STATUSES.has(task.status))
          .map((task) => {
            const patch = vehicleModified[task.id];
            const volume = patch && 'volume' in patch ? patch.volume : task.volume;
            return volume ?? 0;
          });
      })
      .reduce((sum, volume) => sum + volume, 0);

    const createdTotal = Object.values(created)
      .flatMap((tasks) => Object.values(tasks))
      .reduce((sum, task) => sum + (task.volume ?? 0), 0);

    return serverTotal + createdTotal;
  },
);

/**
 * Объединённые свойства определённого транспорта по всем маршрутным заданиям:
 * суммарный объём (м³), вес (тонн) и количество рейсов.
 */
export const selectVehicleAggregates = createSelector([selectMergedVehicleTasks], (tasks) =>
  tasks.reduce(
    (acc, task) => {
      if (EXCLUDED_TOTAL_STATUSES.has(task.status)) return acc;

      return {
        volume: acc.volume + (task.volume ?? 0),
        weight: acc.weight + (task.weight ?? 0),
        trips: acc.trips + (task.plannedTripsCount ?? 0),
      };
    },
    { volume: 0, weight: 0, trips: 0 },
  ),
);

/**
 * Плотность груза для маршрутного задания (через place → cargo_type → loadType.density).
 * Возвращает null если данные недоступны.
 */
export const selectCargoDensity = createSelector(
  [
    selectMergedVehicleTask,
    placeRtkApi.endpoints.getAllPlaces.select(),
    loadTypesRtkApi.endpoints.getAllLoadType.select(),
  ],
  (task, placesResult, loadTypesResult) => {
    if (!hasValue(task?.placeStartId)) return null;

    const places = placesResult.data?.items;
    if (!places) return null;

    const place = places.find((p) => p.id === task.placeStartId);
    if (!hasValue(place?.cargo_type)) return null;

    const loadTypes = loadTypesResult.data;
    if (!loadTypes) return null;

    const loadType = loadTypes.entities[place.cargo_type];
    return hasValue(loadType?.density) ? loadType.density : null;
  },
);
