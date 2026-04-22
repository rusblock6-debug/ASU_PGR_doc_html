import type { PayloadAction } from '@reduxjs/toolkit';
import { createSlice } from '@reduxjs/toolkit';

import type { ShiftTask } from '@/shared/api/endpoints/shift-tasks';

import type {
  CurrentShift,
  RouteTaskDraft,
  RouteTaskEditableField,
  StatusFilterValue,
  TaskBlockState,
  TaskWarningState,
  WorkOrderState,
} from './types';
import { createEmptyTask, emptyTaskFields, mapServerTaskToDraft, pruneEmptyCreatedTasks } from './utils';

const initialState: WorkOrderState = {
  currentShift: null,
  selectedVehicleIds: [],
  selectedStatus: 'all',
  created: {},
  modified: {},
  deleted: {},
  validationErrors: {},
  validationWarnings: {},
  isSubmitBlocked: false,
};

export const slice = createSlice({
  name: 'workOrder',
  initialState,
  reducers: {
    /**
     * Установить параметры текущей смены.
     */
    setCurrentShift(state, action: PayloadAction<CurrentShift>) {
      const { shiftDate, shiftNum, workRegimeId } = action.payload;
      const current = state.currentShift;

      if (
        current &&
        current.shiftDate === shiftDate &&
        current.shiftNum === shiftNum &&
        current.workRegimeId === workRegimeId
      ) {
        return;
      }

      state.currentShift = action.payload;
      state.validationErrors = {};
      state.validationWarnings = {};
      state.isSubmitBlocked = false;
      state.created = {};
      state.modified = {};
      state.deleted = {};
    },

    /**
     * Добавить машины в фильтр.
     */
    addVehiclesToFilter(state, action: PayloadAction<readonly number[]>) {
      state.selectedVehicleIds = [...new Set([...state.selectedVehicleIds, ...action.payload])];
      state.isSubmitBlocked = false;
    },

    /**
     * Убрать машины из фильтра.
     */
    removeVehiclesFromFilter(state, action: PayloadAction<readonly number[]>) {
      const toRemove = new Set(action.payload);
      state.selectedVehicleIds = state.selectedVehicleIds.filter((id) => !toRemove.has(id));
      state.isSubmitBlocked = false;
    },

    /**
     * Установить фильтр по статусу маршрутных заданий.
     */
    setSelectedStatus(state, action: PayloadAction<StatusFilterValue>) {
      state.selectedStatus = action.payload;
      state.isSubmitBlocked = false;
    },

    /**
     * Добавить новое задание к машине.
     */
    addTask(state, action: PayloadAction<{ vehicleId: number }>) {
      const { vehicleId } = action.payload;
      const task = createEmptyTask();

      if (!state.created[vehicleId]) {
        state.created[vehicleId] = {};
      }

      state.created[vehicleId][task.id] = task;
    },

    /**
     * Инициализирует пустые задания для машин без данных.
     * Если активен фильтр по статусу — заглушки не создаются,
     * показываются только машины с найденными заданиями.
     */
    initializeMissingTasks(
      state,
      action: PayloadAction<{
        vehicleIds: readonly number[];
        shiftTasks: readonly ShiftTask[];
      }>,
    ) {
      const { vehicleIds, shiftTasks } = action.payload;
      const hasStatusFilter = state.selectedStatus !== 'all';

      // При активном фильтре не создаём заглушки — удаляем все записи из created.
      if (hasStatusFilter) {
        for (const vid of Object.keys(state.created)) {
          delete state.created[Number(vid)];
        }
        return;
      }

      const vehiclesWithTasks = new Set(
        shiftTasks.filter((task) => task.route_tasks.length > 0).map((task) => task.vehicle_id),
      );

      const vehicleIdSet = new Set(vehicleIds);

      // Удаляем записи для машин, которых нет в списке или у которых есть серверные задания
      for (const vid of Object.keys(state.created)) {
        const vehicleId = Number(vid);

        if (!vehicleIdSet.has(vehicleId)) {
          delete state.created[vehicleId];
          continue;
        }

        if (vehiclesWithTasks.has(vehicleId)) {
          pruneEmptyCreatedTasks(state.created, vehicleId);
        }
      }

      // Добавляем пустые задания для машин без данных (только если записи ещё нет)
      for (const vehicleId of vehicleIds) {
        if (vehiclesWithTasks.has(vehicleId)) continue;
        if (state.created[vehicleId] && Object.keys(state.created[vehicleId]).length > 0) continue;

        const task = createEmptyTask();
        state.created[vehicleId] = { [task.id]: task };
      }
    },

    /**
     * Удалить задание по taskId.
     */
    removeTask(state, action: PayloadAction<{ vehicleId: number; taskId: string }>) {
      const { vehicleId, taskId } = action.payload;

      // Если это новое задание → удаляем из created
      if (state.created[vehicleId]?.[taskId]) {
        delete state.created[vehicleId][taskId];

        // Очищаем машину, если у неё больше нет созданных заданий
        if (Object.keys(state.created[vehicleId]).length === 0) {
          delete state.created[vehicleId];
        }

        return;
      }

      // Если это существующая машина → добавляем в deleted
      if (!state.deleted[vehicleId]) {
        state.deleted[vehicleId] = [];
      }
      state.deleted[vehicleId].push(taskId);

      // Очищаем все измененные поля (modified) задания
      if (state.modified[vehicleId]?.[taskId]) {
        delete state.modified[vehicleId][taskId];

        // Очищаем машину, если у неё больше нет измененных заданий
        if (Object.keys(state.modified[vehicleId]).length === 0) {
          delete state.modified[vehicleId];
        }
      }

      delete state.validationErrors[taskId];
      delete state.validationWarnings[taskId];
    },

    /**
     * Очистить все редактируемые поля задания (сбросить к пустому состоянию).
     */
    clearTask(state, action: PayloadAction<{ vehicleId: number; taskId: string }>) {
      const { vehicleId, taskId } = action.payload;

      delete state.validationWarnings[taskId];

      const createdTask = state.created[vehicleId]?.[taskId];
      if (createdTask) {
        Object.assign(createdTask, emptyTaskFields);
        return;
      }

      if (!state.modified[vehicleId]) {
        state.modified[vehicleId] = {};
      }

      state.modified[vehicleId][taskId] = { ...emptyTaskFields };
    },

    /**
     * Сбросить все созданные задания к пустым полям.
     */
    clearAllTasks(state) {
      for (const vehicleTasks of Object.values(state.created)) {
        for (const task of Object.values(vehicleTasks)) {
          Object.assign(task, emptyTaskFields);
          delete state.validationErrors[task.id];
          delete state.validationWarnings[task.id];
        }
      }
    },

    /**
     * Установить ошибку валидации для задания.
     */
    setValidationError(state, action: PayloadAction<{ taskId: string; error: TaskBlockState }>) {
      const { taskId, error } = action.payload;
      state.validationErrors[taskId] = { ...error, errorFields: [...error.errorFields] };
      state.isSubmitBlocked = true;
    },

    /**
     * Установить ошибки валидации для заданий.
     */
    setValidationErrors(state, action: PayloadAction<Record<string, TaskBlockState>>) {
      for (const [taskId, error] of Object.entries(action.payload)) {
        state.validationErrors[taskId] = { ...error, errorFields: [...error.errorFields] };
      }
      if (Object.keys(action.payload).length > 0) {
        state.isSubmitBlocked = true;
      }
    },

    /**
     * Установить предупреждение валидации для задания.
     */
    setValidationWarning(state, action: PayloadAction<{ taskId: string; warning: TaskWarningState }>) {
      const { taskId, warning } = action.payload;
      state.validationWarnings[taskId] = { ...warning, warningFields: [...warning.warningFields] };
    },

    /**
     * Очистить ошибку валидации для конкретного поля задания.
     */
    clearFieldValidationError(state, action: PayloadAction<{ taskId: string; field: RouteTaskEditableField }>) {
      const { taskId, field } = action.payload;
      const error = state.validationErrors[taskId];
      if (!error) return;

      error.errorFields = error.errorFields.filter((item) => item !== field);
      if (error.errorFields.length === 0) {
        delete state.validationErrors[taskId];
      }

      state.isSubmitBlocked = false;
    },

    /**
     * Очистить предупреждения валидации для конкретных полей задания.
     */
    clearFieldValidationWarning(
      state,
      action: PayloadAction<{ taskId: string; fields: readonly RouteTaskEditableField[] }>,
    ) {
      const { taskId, fields } = action.payload;
      const warning = state.validationWarnings[taskId];
      if (!warning) return;

      warning.warningFields = warning.warningFields.filter((item) => !fields.includes(item));
      if (warning.warningFields.length === 0) {
        delete state.validationWarnings[taskId];
      }
    },

    /**
     * Применить данные из предыдущей смены.
     * Для машин из preview: конвертируем route_tasks в черновики (новый id, статус RouteStatus.EMPTY).
     * Заменяем существующие локальные задания для этих машин.
     * Очищаем ошибки валидации.
     */
    applyPreviousTasks(state, action: PayloadAction<readonly ShiftTask[]>) {
      const previousShiftTasks = action.payload;

      for (const shiftTask of previousShiftTasks) {
        const vehicleId = shiftTask.vehicle_id;
        const routeTasks = shiftTask.route_tasks;

        // Очищаем старые локальные данные для машины
        delete state.created[vehicleId];
        delete state.modified[vehicleId];
        delete state.deleted[vehicleId];

        if (routeTasks.length > 0) {
          state.created[vehicleId] = {};
          for (const routeTask of routeTasks) {
            const draft: RouteTaskDraft = mapServerTaskToDraft(routeTask);
            state.created[vehicleId][draft.id] = draft;
          }
        } else {
          const task = createEmptyTask();
          state.created[vehicleId] = { [task.id]: task };
        }
      }

      for (const shiftTask of previousShiftTasks) {
        const createdTasks = state.created[shiftTask.vehicle_id];
        if (createdTasks) {
          for (const taskId of Object.keys(createdTasks)) {
            delete state.validationErrors[taskId];
            delete state.validationWarnings[taskId];
          }
        }
      }

      state.isSubmitBlocked = false;
    },

    /**
     * Обновить поле в созданном задании (created).
     */
    updateCreatedTask<T extends RouteTaskEditableField>(
      state: WorkOrderState,
      action: PayloadAction<{
        vehicleId: number;
        taskId: string;
        field: T;
        value: RouteTaskDraft[T];
      }>,
    ) {
      const { vehicleId, taskId, field, value } = action.payload;
      const task = state.created[vehicleId]?.[taskId];

      if (task) {
        task[field] = value;
      }
    },

    /**
     * Добавить изменение в существующем задании (modified).
     */
    setModification<T extends RouteTaskEditableField>(
      state: WorkOrderState,
      action: PayloadAction<{
        vehicleId: number;
        taskId: string;
        field: T;
        value: RouteTaskDraft[T];
      }>,
    ) {
      const { vehicleId, taskId, field, value } = action.payload;

      if (!state.modified[vehicleId]) {
        state.modified[vehicleId] = {};
      }

      if (!state.modified[vehicleId][taskId]) {
        state.modified[vehicleId][taskId] = {};
      }

      state.modified[vehicleId][taskId][field] = value;
    },

    /**
     * Убрать изменение у поля в modified (вернулась к начальному значению).
     */
    removeModification(
      state,
      action: PayloadAction<{
        vehicleId: number;
        taskId: string;
        field: RouteTaskEditableField;
      }>,
    ) {
      const { vehicleId, taskId, field } = action.payload;
      const modifications = state.modified[vehicleId]?.[taskId];

      if (modifications) {
        delete modifications[field];

        // Если нет больше изменений для задания, удаляем запись
        if (Object.keys(modifications).length === 0) {
          delete state.modified[vehicleId][taskId];

          // Если нет больше изменений для машины, удаляем запись
          if (Object.keys(state.modified[vehicleId]).length === 0) {
            delete state.modified[vehicleId];
          }
        }
      }
    },

    /**
     * Очистить локальные изменения для заданий с не редактируемым статусом.
     */
    clearNonEditableTaskChanges(state, action: PayloadAction<{ tasks: { vehicleId: number; taskId: string }[] }>) {
      const { tasks } = action.payload;

      for (const { vehicleId, taskId } of tasks) {
        if (state.modified[vehicleId]?.[taskId]) {
          delete state.modified[vehicleId][taskId];
          if (Object.keys(state.modified[vehicleId]).length === 0) {
            delete state.modified[vehicleId];
          }
        }

        if (state.deleted[vehicleId]) {
          const index = state.deleted[vehicleId].indexOf(taskId);
          if (index !== -1) {
            state.deleted[vehicleId].splice(index, 1);
            if (state.deleted[vehicleId].length === 0) {
              delete state.deleted[vehicleId];
            }
          }
        }

        delete state.validationErrors[taskId];
        delete state.validationWarnings[taskId];
      }
    },

    /**
     * Сброс несохранённых изменений.
     */
    resetUnsavedChanges(state) {
      state.created = {};
      state.modified = {};
      state.deleted = {};
      state.validationErrors = {};
      state.validationWarnings = {};
      state.isSubmitBlocked = false;
    },

    /**
     * Очистить изменения после успешной отправки.
     */
    clearSubmittedEdits(
      state,
      action: PayloadAction<{
        vehicleIds: number[];
      }>,
    ) {
      const { vehicleIds } = action.payload;

      for (const vehicleId of vehicleIds) {
        const createdTasks = state.created[vehicleId];
        if (createdTasks) {
          for (const taskId of Object.keys(createdTasks)) {
            delete state.validationErrors[taskId];
            delete state.validationWarnings[taskId];
          }
        }

        const modifiedTasks = state.modified[vehicleId];
        if (modifiedTasks) {
          for (const taskId of Object.keys(modifiedTasks)) {
            delete state.validationErrors[taskId];
            delete state.validationWarnings[taskId];
          }
        }

        delete state.created[vehicleId];
        delete state.modified[vehicleId];
        delete state.deleted[vehicleId];
      }

      state.isSubmitBlocked = false;
    },
  },
});

export const workOrderActions = slice.actions;
export const workOrderReducer = slice.reducer;
