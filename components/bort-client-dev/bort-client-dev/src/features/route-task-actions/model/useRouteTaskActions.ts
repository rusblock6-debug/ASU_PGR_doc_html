import { isRouteTaskFinished, isRouteTaskInProgress } from '@/entities/route-task';

import {
  useActivateRouteTaskMutation,
  useCancelRouteTaskMutation,
  useCompleteActiveTripMutation,
  useGetActiveTaskQuery,
  useUpdateRouteTaskMutation,
} from '@/shared/api';
import type { RouteTaskResponse } from '@/shared/api/types/trip-service';
import { extractActiveRouteTaskIdFromPayload } from '@/shared/lib/active-route-task';

/**
 * Опции хука действий маршрутного задания.
 */
interface RouteTaskActionsOptions {
  readonly onActivated?: () => void;
}

/**
 * Мутации управления маршрутным заданием (активация, пауза, отмена, завершение рейса).
 */
export const useRouteTaskActions = (task: RouteTaskResponse | null, options?: RouteTaskActionsOptions) => {
  const { data: activeTask } = useGetActiveTaskQuery();
  const [activate, activateState] = useActivateRouteTaskMutation();
  const [cancel, cancelState] = useCancelRouteTaskMutation();
  const [updateTask, pauseState] = useUpdateRouteTaskMutation();
  const [completeTrip, completeState] = useCompleteActiveTripMutation();

  const activeTaskId = extractActiveRouteTaskIdFromPayload(activeTask);

  const isThisTaskActive = task != null && activeTaskId === task.id;

  let primaryLabel = 'ПРИСТУПИТЬ';
  if (task && isRouteTaskInProgress(task.status) && isThisTaskActive) {
    primaryLabel = 'ЗАВЕРШИТЬ';
  }

  const handleActivate = async () => {
    if (!task) {
      return;
    }
    await activate({ taskId: task.id }).unwrap();
    options?.onActivated?.();
  };

  const handleCancelTask = async () => {
    if (!task) {
      return;
    }
    await cancel({ taskId: task.id }).unwrap();
  };

  const handlePause = async () => {
    if (!task) {
      return;
    }
    await updateTask({ taskId: task.id, body: { status: 'PAUSED' } }).unwrap();
  };

  const handleCompleteTrip = async () => {
    await completeTrip().unwrap();
  };

  const handlePrimary = async () => {
    if (!task) {
      return;
    }
    if (isRouteTaskInProgress(task.status) && isThisTaskActive) {
      await handleCompleteTrip();
      return;
    }
    await handleActivate();
  };

  const disabled = !task || isRouteTaskFinished(task.status);

  const isLoading = activateState.isLoading || cancelState.isLoading || pauseState.isLoading || completeState.isLoading;

  return {
    primaryLabel,
    handleCancelTask,
    handlePause,
    handlePrimary,
    disabled,
    isLoading,
    isThisTaskActive,
  };
};
