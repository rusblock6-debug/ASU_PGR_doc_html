import { nanoid } from '@reduxjs/toolkit';

import { calculateFromTrips, calculateFromVolume, calculateFromWeight } from '@/entities/route-task';

import { RouteStatus, TypeTask, type RouteTask } from '@/shared/api/endpoints/route-tasks';
import { assertNever } from '@/shared/lib/assert-never';
import { EMPTY_ARRAY } from '@/shared/lib/constants';
import { hasValueNotEmpty } from '@/shared/lib/has-value';

import type { LinkedField, RouteTaskDraft, RouteTaskEditableFields, WorkOrderState } from './types';

/**
 * Начальные значения для редактируемых полей задания.
 */
export const emptyTaskFields = {
  placeStartId: null,
  placeEndId: null,
  volume: null,
  weight: null,
  plannedTripsCount: null,
  message: null,
  taskType: TypeTask.LOADING_GM,
} as const;

/**
 * Создаёт новую пустую задачу с уникальным ID.
 */
export function createEmptyTask(): RouteTaskDraft {
  return {
    ...emptyTaskFields,
    id: nanoid(),
    status: RouteStatus.EMPTY,
  };
}

/**
 * Объединяет серверные задания с локальными изменениями для одной машины.
 * Применяет изменения к редактируемым заданиям, исключает удалённые, добавляет созданные.
 */
export function mergeVehicleTasks(
  serverRouteTasks: readonly RouteTask[],
  created?: Record<string, RouteTaskDraft>,
  modified?: Record<string, Partial<RouteTaskEditableFields>>,
  deleted?: readonly string[],
) {
  const deletedSet = new Set(deleted ?? EMPTY_ARRAY);

  const merged = serverRouteTasks
    .filter((task) => !deletedSet.has(task.id))
    .map((task) => {
      const draft = mapServerTask(task);
      const patch = modified?.[task.id];
      return patch ? { ...draft, ...patch } : draft;
    });

  const createdTasks = Object.values(created ?? {});
  return [...merged, ...createdTasks];
}

/**
 * Конвертирует маршрутное задание в локальный формат.
 */
export function mapServerTask(task: RouteTask): RouteTaskDraft {
  return {
    id: task.id,
    placeStartId: task.place_a_id,
    placeEndId: task.place_b_id,
    volume: task.volume,
    weight: task.weight,
    plannedTripsCount: task.planned_trips_count,
    message: task.message ?? null,
    taskType: task.type_task,
    status: task.status,
  };
}

/**
 * Конвертирует серверное задание в черновик с новым ID и статусом RouteStatus.EMPTY.
 * Используется при копировании из предыдущей смены.
 */
export function mapServerTaskToDraft(task: RouteTask): RouteTaskDraft {
  return {
    id: nanoid(),
    placeStartId: task.place_a_id,
    placeEndId: task.place_b_id,
    volume: task.volume,
    weight: task.weight,
    plannedTripsCount: task.planned_trips_count,
    message: task.message ?? null,
    taskType: task.type_task,
    status: RouteStatus.EMPTY,
  };
}

/**
 * Проверяет, есть ли у черновика задания пользовательский ввод
 * (хотя бы одно заполненное редактируемое поле).
 */
export function hasTaskUserInput(task: RouteTaskDraft): boolean {
  return (
    hasValueNotEmpty(task.placeStartId) ||
    hasValueNotEmpty(task.placeEndId) ||
    hasValueNotEmpty(task.volume) ||
    hasValueNotEmpty(task.weight) ||
    hasValueNotEmpty(task.plannedTripsCount) ||
    hasValueNotEmpty(task.message)
  );
}

/**
 * Удаляет пустые заглушки из created-заданий машины, сохраняя заполненные.
 * Если после очистки не осталось заданий — удаляет запись целиком.
 */
export function pruneEmptyCreatedTasks(created: WorkOrderState['created'], vehicleId: number) {
  const tasks = created[vehicleId];
  for (const taskId of Object.keys(tasks)) {
    if (!hasTaskUserInput(tasks[taskId])) {
      delete tasks[taskId];
    }
  }
  if (Object.keys(tasks).length === 0) {
    delete created[vehicleId];
  }
}

/**
 * Возвращает заполненное связанное поле.
 * Используется при выборе места погрузки для определения поля пересчёта.
 */
export function getFilledLinkedField(task: RouteTaskDraft): LinkedField | null {
  if (task.volume !== null) return 'volume';
  if (task.weight !== null) return 'weight';
  if (task.plannedTripsCount !== null) return 'plannedTripsCount';
  return null;
}

/**
 * Выбирает функцию расчёта в зависимости от изменённого поля.
 */
export function getCalculator(field: LinkedField) {
  switch (field) {
    case 'volume':
      return calculateFromVolume;
    case 'weight':
      return calculateFromWeight;
    case 'plannedTripsCount':
      return calculateFromTrips;
    default:
      assertNever(field);
  }
}
