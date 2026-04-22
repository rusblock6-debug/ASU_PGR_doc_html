import { useActivateRouteTaskMutation } from '@/shared/api/endpoints/route-tasks';
import { useAppDispatch } from '@/shared/lib/hooks/useAppDispatch';
import { useAppSelector } from '@/shared/lib/hooks/useAppSelector';
import { AppButton } from '@/shared/ui/AppButton';
import { toast } from '@/shared/ui/Toast';

import {
  ASSIGNABLE_STATUSES,
  CANCELLABLE_STATUSES,
  EDITABLE_STATUSES,
  RESUMABLE_STATUSES,
} from '../../model/constants';
import { selectVehicleHasActiveTask, selectVehicleTaskCount } from '../../model/selectors';
import { workOrderActions } from '../../model/slice';
import type { RouteTaskDraft, TaskIdentifier } from '../../model/types';

import { AssignButton } from './AssignButton';
import { CancelButton } from './CancelButton';
import styles from './RouteTaskActions.module.css';

/**
 * Представляет свойства компонента {@link RouteTaskActions}.
 */
interface RouteTaskActionsProps extends TaskIdentifier {
  /** Данные маршрутного задания. */
  readonly task: RouteTaskDraft;
}

/**
 * Представляет кнопки действий для маршрутного задания для конкретного транспорта.
 */
export function RouteTaskActions({ vehicleId, taskId, task }: RouteTaskActionsProps) {
  const [activateRouteTask] = useActivateRouteTaskMutation();

  const dispatch = useAppDispatch();

  const vehicleTaskCount = useAppSelector((state) => selectVehicleTaskCount(state, vehicleId));
  const hasManyVehicleTasks = vehicleTaskCount > 1;

  const hasActiveTask = useAppSelector((state) => selectVehicleHasActiveTask(state, vehicleId));
  const canAssignTask = Boolean(
    task.id && hasManyVehicleTasks && hasActiveTask && ASSIGNABLE_STATUSES.has(task.status),
  );

  const canResumingTask = RESUMABLE_STATUSES.has(task.status);

  const canEditTask = EDITABLE_STATUSES.has(task.status);

  const canCancelTask = CANCELLABLE_STATUSES.has(task.status);

  const handleClearFields = () => {
    dispatch(workOrderActions.clearTask({ vehicleId, taskId }));
  };

  const handleDeleteTask = () => {
    dispatch(workOrderActions.removeTask({ vehicleId, taskId }));
  };

  const handleResumingTask = async () => {
    try {
      await activateRouteTask({ taskId: task.id, vehicleId: String(vehicleId) }).unwrap();
      toast.success({ message: 'Наряд-задание возобновлено' });
    } catch {
      toast.error({ message: 'Не удалось возобновить наряд-задание' });
    }
  };

  return (
    <div className={styles.route_task_header_actions}>
      {canEditTask && (
        <>
          <AppButton
            variant="clear"
            size="xs"
            onClick={handleClearFields}
          >
            Очистить
          </AppButton>

          {hasManyVehicleTasks && (
            <AppButton
              variant="clear"
              size="xs"
              onClick={handleDeleteTask}
            >
              Удалить
            </AppButton>
          )}
        </>
      )}

      {canResumingTask && (
        <AppButton
          variant="clear"
          size="xs"
          onClick={handleResumingTask}
        >
          Возобновить
        </AppButton>
      )}

      {canAssignTask && (
        <AssignButton
          taskId={taskId}
          vehicleId={vehicleId}
        />
      )}

      {canCancelTask && (
        <CancelButton
          taskId={taskId}
          vehicleId={vehicleId}
        />
      )}
    </div>
  );
}
