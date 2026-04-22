import { selectVehicleSpecs } from '@/entities/vehicle';

import { hasValue } from '@/shared/lib/has-value';
import { typedEntries } from '@/shared/lib/typed-entries';

import { isFieldEqual } from '../lib/task-equal';

import { BlockReason } from './block-reasons';
import { selectCargoDensity, selectMergedVehicleTask, selectServerTaskById } from './selectors';
import { workOrderActions } from './slice';
import type { LinkedField, RouteTaskDraft, RouteTaskEditableField } from './types';
import { getCalculator, getFilledLinkedField } from './utils';
import { RouteTaskWarningReason } from './warning-reasons';

/**
 * Обновление связанного поля с автоматическим пересчётом зависимых полей.
 *
 * При вводе объёма → пересчитывает вес и рейсы.
 * При вводе веса → пересчитывает объём и рейсы.
 * При вводе рейсов → пересчитывает вес и объём.
 */
export function updateLinkedField(payload: {
  readonly vehicleId: number;
  readonly taskId: string;
  readonly field: LinkedField;
  readonly value: number | null;
}) {
  return (dispatch: AppDispatch, getState: () => RootState) => {
    const { vehicleId, taskId, field, value } = payload;
    const state = getState();
    const task = selectMergedVehicleTask(state, vehicleId, taskId);

    // Если место погрузки не выбрано — блокируем пересчёт
    if (!hasValue(task?.placeStartId)) {
      dispatch(updateTaskField({ vehicleId, taskId, field, value }));
      dispatch(
        workOrderActions.setValidationError({
          taskId,
          error: { reason: BlockReason.NO_PLACE_START, errorFields: ['placeStartId'] },
        }),
      );
      return;
    }

    // Обновляем введённое поле
    dispatch(updateTaskField({ vehicleId, taskId, field, value }));

    // Получаем данные для расчёта
    const density = selectCargoDensity(state, vehicleId, taskId);
    const vehicle = selectVehicleSpecs(state, vehicleId);

    // Проверяем доступность данных для расчёта
    if (!hasValue(density)) {
      dispatch(
        workOrderActions.setValidationError({
          taskId,
          error: { reason: BlockReason.NO_DENSITY, errorFields: ['placeStartId'] },
        }),
      );
      return;
    }
    if (!hasValue(vehicle.loadCapacity) || !hasValue(vehicle.volumeM3)) {
      dispatch(
        workOrderActions.setValidationError({
          taskId,
          error: { reason: BlockReason.NO_VEHICLE_SPECS, errorFields: [] },
        }),
      );
      return;
    }

    // Считаем зависимые поля
    const params = { density, loadCapacity: vehicle.loadCapacity, volumeM3: vehicle.volumeM3 };
    const calculator = getCalculator(field);
    const calculated = calculator(value, params);

    // Обновляем зависимые поля
    for (const [field, value] of typedEntries(calculated)) {
      dispatch(
        updateTaskField({
          vehicleId,
          taskId,
          field,
          value: hasValue(value) ? value : null,
        }),
      );
    }
  };
}

/**
 * Изменение места погрузки.
 *
 * Если есть заполненное связанное поле (объём, вес, рейс) — пересчитывает от него.
 * Если у места нет груза — блокирует задание.
 */
export function setPlaceStart(payload: {
  readonly vehicleId: number;
  readonly taskId: string;
  readonly placeStartId: number | null;
  readonly hasCargo: boolean;
  readonly isUnmatchedCargoType?: boolean;
}) {
  return (dispatch: AppDispatch, getState: () => RootState) => {
    const { vehicleId, taskId, placeStartId, hasCargo, isUnmatchedCargoType } = payload;

    dispatch(workOrderActions.clearFieldValidationWarning({ taskId, fields: ['placeStartId', 'placeEndId'] }));

    if (isUnmatchedCargoType) {
      dispatch(
        workOrderActions.setValidationWarning({
          taskId,
          warning: {
            reason: RouteTaskWarningReason.MISMATCH_TYPE_CARGO,
            warningFields: ['placeStartId', 'placeEndId'],
          },
        }),
      );
    }

    // Обновляем поле места погрузки
    dispatch(updateTaskField({ vehicleId, taskId, field: 'placeStartId', value: placeStartId }));

    // Выходим, если место погрузки не выбрано
    if (!hasValue(placeStartId)) {
      return;
    }

    // Блокируем, если у места погрузки нет груза
    if (!hasCargo) {
      dispatch(
        workOrderActions.setValidationError({
          taskId,
          error: { reason: BlockReason.NO_CARGO, errorFields: ['placeStartId'] },
        }),
      );
      return;
    }

    // Если есть заполненное связанное поле (объём, вес, рейс) пересчитываем от него
    const state = getState();
    const task = selectMergedVehicleTask(state, vehicleId, taskId);
    const filledField = task ? getFilledLinkedField(task) : null;

    if (filledField && task) {
      dispatch(updateLinkedField({ vehicleId, taskId, field: filledField, value: task[filledField] }));
    }
  };
}

/**
 * Обновление поля задачи.
 * Автоматически определяет куда положить изменения (это создание/редактирование).
 */
export const updateTaskField =
  (payload: {
    readonly vehicleId: number;
    readonly taskId: string;
    readonly field: RouteTaskEditableField;
    readonly value: RouteTaskDraft[RouteTaskEditableField];
    readonly isUnmatchedCargoType?: boolean;
  }) =>
  (dispatch: AppDispatch, getState: () => RootState) => {
    const { vehicleId, taskId, field, value, isUnmatchedCargoType } = payload;
    const state = getState();
    const { created } = state.workOrder;

    dispatch(workOrderActions.clearFieldValidationError({ taskId, field }));

    if (field === 'placeEndId') {
      dispatch(workOrderActions.clearFieldValidationWarning({ taskId, fields: [field, 'placeStartId'] }));
    }

    if (isUnmatchedCargoType) {
      dispatch(
        workOrderActions.setValidationWarning({
          taskId,
          warning: {
            reason: RouteTaskWarningReason.MISMATCH_TYPE_CARGO,
            warningFields: ['placeStartId', 'placeEndId'],
          },
        }),
      );
    }

    const createdTask = created[vehicleId]?.[taskId];
    if (createdTask) {
      dispatch(workOrderActions.updateCreatedTask({ vehicleId, taskId, field, value }));
      return;
    }

    const serverTask = selectServerTaskById(state, taskId);
    if (!serverTask) return;

    if (isFieldEqual(field, value, serverTask)) {
      dispatch(workOrderActions.removeModification({ vehicleId, taskId, field }));
    } else {
      dispatch(workOrderActions.setModification({ vehicleId, taskId, field, value }));
    }
  };
