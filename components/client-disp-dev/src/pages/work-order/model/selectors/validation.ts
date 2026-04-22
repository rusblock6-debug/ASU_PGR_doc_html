import { createSelector } from '@reduxjs/toolkit';

import { hasTaskUserInput } from '../utils';

import { selectMergedVehicleTasks } from './merged-tasks';

/**
 * Ошибка валидации задания по taskId.
 */
export const selectValidationError = createSelector(
  [(state: RootState) => state.workOrder.validationErrors, (_state: RootState, taskId: string) => taskId],
  (errors, taskId) => errors[taskId] ?? null,
);

/**
 * Предупреждение валидации задания по taskId.
 */
export const selectValidationWarning = createSelector(
  [(state: RootState) => state.workOrder.validationWarnings, (_state: RootState, taskId: string) => taskId],
  (warnings, taskId) => warnings[taskId] ?? null,
);

/**
 * Есть ли хотя бы одно маршрутное задание машины с ошибкой валидации.
 */
export const selectVehicleHasError = createSelector(
  [selectMergedVehicleTasks, (state: RootState) => state.workOrder.validationErrors],
  (tasks, validationErrors) => tasks.some((task) => task.id in validationErrors),
);

/**
 * Есть ли хотя бы одно маршрутное задание машины с предупреждением валидации.
 */
export const selectVehicleHasWarning = createSelector(
  [selectMergedVehicleTasks, (state: RootState) => state.workOrder.validationWarnings],
  (tasks, validationWarnings) => tasks.some((task) => task.id in validationWarnings),
);

/**
 * Есть ли хотя бы одно задание со статусом `empty` («К заполнению»).
 */
export const selectHasEmptyStatusTask = (state: RootState) => {
  const { created } = state.workOrder;

  for (const vehicleTasks of Object.values(created)) {
    if (Object.keys(vehicleTasks).length > 0) {
      return true;
    }
  }

  return false;
};

/**
 * Количество машин и маршрутных заданий со статусом `empty` («К заполнению»).
 */
export const selectEmptyStatusStats = createSelector([(state: RootState) => state.workOrder.created], (created) => {
  let vehiclesCount = 0;
  let tasksCount = 0;

  for (const vehicleTasks of Object.values(created)) {
    const count = Object.keys(vehicleTasks).length;
    if (count > 0) {
      vehiclesCount++;
      tasksCount += count;
    }
  }

  return { vehiclesCount, tasksCount };
});

/**
 * Возвращает ID-машин с несохранёнными изменениями.
 */
export const selectDirtyVehicleIds = createSelector(
  [
    (state: RootState) => state.workOrder.created,
    (state: RootState) => state.workOrder.modified,
    (state: RootState) => state.workOrder.deleted,
  ],
  (created, modified, deleted) => {
    const dirtyIds = new Set<number>();

    for (const vehicleId of Object.keys(created)) {
      const hasDirtyTask = Object.values(created[Number(vehicleId)]).some(hasTaskUserInput);

      if (hasDirtyTask) {
        dirtyIds.add(Number(vehicleId));
      }
    }

    // Машины с изменёнными заданиями
    for (const vehicleId of Object.keys(modified)) {
      if (Object.keys(modified[Number(vehicleId)]).length > 0) {
        dirtyIds.add(Number(vehicleId));
      }
    }

    // Машины с удалёнными заданиями
    for (const vehicleId of Object.keys(deleted)) {
      if (deleted[Number(vehicleId)].length > 0) {
        dirtyIds.add(Number(vehicleId));
      }
    }

    return [...dirtyIds];
  },
);

/**
 * Возвращает ID-машин с любыми локальными записями (включая пустые заглушки).
 * Используется при отправке, чтобы валидация затронула все задания.
 */
export const selectAllChangedVehicleIds = createSelector(
  [
    (state: RootState) => state.workOrder.created,
    (state: RootState) => state.workOrder.modified,
    (state: RootState) => state.workOrder.deleted,
  ],
  (created, modified, deleted) => {
    const ids = new Set<number>();

    for (const vehicleId of Object.keys(created)) {
      if (Object.keys(created[Number(vehicleId)]).length > 0) {
        ids.add(Number(vehicleId));
      }
    }

    for (const vehicleId of Object.keys(modified)) {
      if (Object.keys(modified[Number(vehicleId)]).length > 0) {
        ids.add(Number(vehicleId));
      }
    }

    for (const vehicleId of Object.keys(deleted)) {
      if (deleted[Number(vehicleId)].length > 0) {
        ids.add(Number(vehicleId));
      }
    }

    return [...ids];
  },
);

/**
 * Есть ли несохранённые изменения.
 */
export const selectHasChanges = createSelector(
  [selectDirtyVehicleIds],
  (dirtyVehicleIds) => dirtyVehicleIds.length > 0,
);

/**
 * Заблокирована ли отправка после неудачной валидации.
 */
export const selectIsSubmitBlocked = (state: RootState) => state.workOrder.isSubmitBlocked;
