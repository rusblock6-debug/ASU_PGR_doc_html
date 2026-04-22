import { createSelector } from '@reduxjs/toolkit';

import { selectAllVehicleIds } from '@/entities/vehicle';

import type { ShiftTasksQueryArg } from '@/shared/api/endpoints/shift-tasks';

import { STATUS_FILTER_MAP } from '../constants';

/**
 * Параметры текущей смены.
 */
export const selectCurrentShift = (state: RootState) => state.workOrder.currentShift;

/**
 * Фильтр по выбранным машинам.
 */
export const selectSelectedVehicleIds = (state: RootState) => state.workOrder.selectedVehicleIds;

/**
 * Фильтр по статусу маршрутного задания.
 */
export const selectSelectedStatus = (state: RootState) => state.workOrder.selectedStatus;

/**
 * Аргументы с которыми делаем запрос за получением наряд-заданий.
 * Когда смена не определена, возвращаем заглушку
 * запрос всё равно пропускается через `skip: !isShiftReady`.
 */
export const selectShiftTasksQueryArg = createSelector(
  [selectCurrentShift, selectSelectedVehicleIds, selectSelectedStatus],
  (currentShift, vehicleIds, statusFilter): ShiftTasksQueryArg => ({
    shift_date: currentShift?.shiftDate ?? '',
    shift_num: currentShift?.shiftNum ?? 0,
    vehicle_ids: vehicleIds.length > 0 ? vehicleIds : undefined,
    status_route_tasks: STATUS_FILTER_MAP[statusFilter],
  }),
);

/**
 * Возвращает список машин отфильтрованные по selectedVehicleIds.
 * Пустой selectedVehicleIds = все машины.
 */
export const selectFilteredVehicleIds = createSelector(
  [selectAllVehicleIds, selectSelectedVehicleIds],
  (allIds, selectedIds): readonly number[] => {
    if (selectedIds.length === 0) return allIds;
    return allIds.filter((id) => selectedIds.includes(id));
  },
);
