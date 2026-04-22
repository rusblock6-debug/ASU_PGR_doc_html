import { isRouteTaskFinished } from '@/entities/route-task';

import type { TripStatusRouteEnum } from '@/shared/api/endpoints/tasks';
import type { RouteTaskResponse } from '@/shared/api/endpoints/tasks';
import {
  useActivateRouteTaskMutation,
  useCompleteActiveTripMutation,
  useUpdateRouteTaskMutation,
} from '@/shared/api/endpoints/tasks';
import { hasValue } from '@/shared/lib/has-value';

/** Опции хука `useRouteTaskActions` (колбэки после действий). */
interface RouteTaskActionsOptions {
  readonly onStarted?: () => void;
}

/**
 * Мутации управления статусом маршрутного задания + disabled-состояния кнопок.
 */
export const useRouteTaskActions = (task: RouteTaskResponse | null, options?: RouteTaskActionsOptions) => {
  const [activateTask, activateTaskState] = useActivateRouteTaskMutation();
  const [updateTask, updateTaskState] = useUpdateRouteTaskMutation();
  const [completeTrip, completeTripState] = useCompleteActiveTripMutation();

  const updateStatus = async (status: TripStatusRouteEnum) => {
    if (!task) {
      return;
    }
    await updateTask({ taskId: task.id, body: { status } }).unwrap();
  };

  const handleStart = async () => {
    if (!task) {
      return;
    }
    await activateTask({ taskId: task.id }).unwrap();
    options?.onStarted?.();
  };

  const handlePause = async () => {
    await updateStatus('PAUSED');
  };

  const handleComplete = async () => {
    await completeTrip().unwrap();
  };

  const handleCancel = async () => {
    await updateStatus('REJECTED');
  };

  const isLoading = activateTaskState.isLoading || updateTaskState.isLoading || completeTripState.isLoading;
  const finished = hasValue(task) && isRouteTaskFinished(task.status);
  const base = !task || isLoading;

  const disabledMap = (() => {
    if (finished) {
      return { start: true, pause: true, complete: true, cancel: true };
    }
    return {
      start: base || task?.status === 'IN_PROGRESS',
      pause: base || task?.status === 'PAUSED' || task?.status === 'REJECTED',
      complete: base || task?.status === 'REJECTED',
      cancel: base,
    };
  })();

  return {
    handleStart,
    handlePause,
    handleComplete,
    handleCancel,
    isLoading,
    disabledMap,
  };
};
