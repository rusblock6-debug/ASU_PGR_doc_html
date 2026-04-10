import { useEffect, useMemo, useRef } from 'react';

import type { ShiftTask, ShiftTaskStreamMessage } from '@/shared/api/endpoints/shift-tasks';
import { shiftTaskRtkApi, useGetShiftTasksStreamQuery } from '@/shared/api/endpoints/shift-tasks';
import { useGetAllVehiclesQuery } from '@/shared/api/endpoints/vehicles';
import { hasValue } from '@/shared/lib/has-value';
import { useAppDispatch } from '@/shared/lib/hooks/useAppDispatch';
import { useAppSelector } from '@/shared/lib/hooks/useAppSelector';

import { useHighlightedVehicles } from '../lib/hooks/useHighlightedVehicles';

import { EDITABLE_STATUSES, STATUS_FILTER_MAP } from './constants';
import {
  selectCurrentShift,
  selectSelectedStatus,
  selectSelectedVehicleIds,
  selectShiftTasksQueryArg,
} from './selectors';
import { workOrderActions } from './slice';
import type { StatusFilterValue } from './types';

const EMPTY_EVENTS: readonly ShiftTaskStreamMessage[] = [];

/**
 * Представляет параметры хука useShiftTasksStream.
 */
interface UseShiftTasksStreamOptions {
  /** Отключить обработку SSE. */
  readonly disabled?: boolean;
  /** Перезапрашивает наряд-задания с сервера после успешной отправки. */
  readonly refetchShiftTasks: () => Promise<unknown>;
}

/**
 * Структура кеша ShiftTask.
 */
interface InfiniteQueryDraft {
  /** Загруженные страницы infinite-запроcа. */
  readonly pages: { readonly items: ShiftTask[] }[];
}

/**
 * Хук для обработки SSE обновлений наряд-заданий в реальном времени.
 *
 * При получении события:
 * 1. Фильтрация по текущей смене.
 * 2. Обновление RTK Query кеша, локальные изменения (created/modified) не затрагиваются.
 * 3. При не редактируемом статусе задачи → очистка локальных изменений (modified/deleted).
 * 4. При новой машине → запрос на получение всего списка машин.
 *
 * Если форма отправляется → disabled === true — значит игнорируем Server-Sent Events.
 * При reconnect после ошибки — полный refetch данных.
 */
export function useShiftTasksStream({ disabled, refetchShiftTasks }: UseShiftTasksStreamOptions) {
  const dispatch = useAppDispatch();
  const currentShift = useAppSelector(selectCurrentShift);
  const queryArg = useAppSelector(selectShiftTasksQueryArg);
  const selectedVehicleIds = useAppSelector(selectSelectedVehicleIds);
  const selectedStatus = useAppSelector(selectSelectedStatus);

  const { data: vehiclesData, refetch: refetchVehicles } = useGetAllVehiclesQuery();
  const vehicleIds = useMemo(() => vehiclesData?.ids ?? [], [vehiclesData?.ids]);

  const { data: events = EMPTY_EVENTS, isSuccess, isError } = useGetShiftTasksStreamQuery();
  const { highlightedIds, addHighlight } = useHighlightedVehicles();

  const wasErrorRef = useRef(false);
  const processedCountRef = useRef(0);

  useEffect(() => {
    if (isError) wasErrorRef.current = true;
    if (isSuccess && wasErrorRef.current) {
      wasErrorRef.current = false;
      void refetchShiftTasks();
    }
  }, [isSuccess, isError, refetchShiftTasks]);

  // SSE-события складываются в массив `events` (RTK-кеш `getShiftTasksStream`).
  // React батчит рендеры, поэтому между вызовами useEffect может прийти несколько событий.
  // Чтобы ни одно событие не потерялось, отслеживаем индекс последнего обработанного
  // через `processedCountRef` и при каждом вызове обрабатываем только новые элементы.
  // eslint-disable-next-line sonarjs/cognitive-complexity
  useEffect(() => {
    // После unmount/remount кеш сбрасывается → массив, начинается заново
    if (events.length < processedCountRef.current) {
      processedCountRef.current = 0;
    }

    // Нет новых событий
    if (events.length === processedCountRef.current) return;

    // Во время отправки пропускаем события, это ок, т.к. после отправки данных переполучаем актуальные данные
    if (disabled) {
      processedCountRef.current = events.length;
      return;
    }

    const newEvents = events.slice(processedCountRef.current);
    processedCountRef.current = events.length;

    for (const event of newEvents) {
      // eslint-disable-next-line @typescript-eslint/naming-convention
      const { action, shift_task, vehicle_id } = event;

      const isCurrentShift =
        hasValue(currentShift) &&
        shift_task?.shift_date === currentShift.shiftDate &&
        shift_task?.shift_num === currentShift.shiftNum;

      // Новая машина → refetch vehicles
      if (action === 'create' && !vehicleIds.includes(vehicle_id)) {
        void refetchVehicles();
      }

      if (!isCurrentShift) continue;
      if (selectedVehicleIds.length > 0 && !selectedVehicleIds.includes(vehicle_id)) continue;

      const cacheEvent = applyStatusFilter(event, selectedStatus);

      addHighlight(vehicle_id);

      // Обновить RTK кеш
      dispatch(
        shiftTaskRtkApi.util.updateQueryData('getShiftTasks', queryArg, (draft) =>
          updateShiftTasksCache(draft as InfiniteQueryDraft, cacheEvent),
        ),
      );

      // При обновлении — очистить локальные изменения для задач с не редактируемым статусом
      if (action === 'update' && shift_task) {
        const nonEditableTasks = shift_task.route_tasks
          .filter((task) => !EDITABLE_STATUSES.has(task.status))
          .map((task) => ({ vehicleId: vehicle_id, taskId: task.id }));

        if (nonEditableTasks.length > 0) {
          dispatch(workOrderActions.clearNonEditableTaskChanges({ tasks: nonEditableTasks }));
        }
      }
    }
  }, [
    events,
    disabled,
    currentShift,
    queryArg,
    selectedStatus,
    selectedVehicleIds,
    vehicleIds,
    dispatch,
    refetchVehicles,
    addHighlight,
  ]);

  return highlightedIds;
}

/**
 * Применить фильтр по статусу к SSE-событию.
 * Если активен фильтр оставляет только `route_tasks` с подходящим статусом.
 * При отсутствии подходящих задач → событие превращается в delete (машина убирается из RTK-кеша).
 */
function applyStatusFilter(event: ShiftTaskStreamMessage, selectedStatus: StatusFilterValue): ShiftTaskStreamMessage {
  const statusFilter = STATUS_FILTER_MAP[selectedStatus];
  if (!statusFilter || !event.shift_task) return event;

  const filteredRouteTasks = event.shift_task.route_tasks.filter((task) => statusFilter.includes(task.status));

  if (filteredRouteTasks.length === 0) {
    return { ...event, action: 'delete', shift_task: undefined };
  }

  if (filteredRouteTasks.length !== event.shift_task.route_tasks.length) {
    return { ...event, shift_task: { ...event.shift_task, route_tasks: filteredRouteTasks } };
  }

  return event;
}

/**
 * Обновить RTK Query кеш — простая замена серверными данными.
 */
function updateShiftTasksCache(draft: InfiniteQueryDraft, event: ShiftTaskStreamMessage) {
  // eslint-disable-next-line @typescript-eslint/naming-convention
  const { action, shift_task, vehicle_id } = event;

  for (const page of draft.pages) {
    const index = page.items.findIndex((st: ShiftTask) => st.vehicle_id === vehicle_id);

    if (action === 'delete') {
      if (index !== -1) page.items.splice(index, 1);
      return;
    }

    if (!shift_task) return;

    if (index !== -1) {
      page.items[index] = shift_task;
      return;
    }
  }

  if (action === 'create' && shift_task && draft.pages.length > 0) {
    draft.pages[0].items.push(shift_task);
  }
}
