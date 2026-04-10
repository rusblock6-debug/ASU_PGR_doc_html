import { useActivateRouteTaskMutation } from '@/shared/api/endpoints/route-tasks';
import { useConfirm } from '@/shared/lib/confirm';
import { useAppSelector } from '@/shared/lib/hooks/useAppSelector';
import { AppButton } from '@/shared/ui/AppButton';
import { toast } from '@/shared/ui/Toast';

import { formatTaskDescription } from '../../lib/format-task-description';
import { useRouteTaskData } from '../../lib/hooks/useRouteTaskData';
import { ACTIVE_STATUS } from '../../model/constants';
import { selectMergedVehicleTask, selectMergedVehicleTasks } from '../../model/selectors';
import type { TaskIdentifier } from '../../model/types';

/**
 * Кнопка назначения маршрутного задания с подтверждением.
 * Показывает диалог подтверждения с деталями задания в статусе «В работе» перед назначением.
 * При подтверждении приостанавливает активное задание в статусе «В работе»,
 * переводит выбранное задание в статус «В работе» и показывает уведомление.
 */
export function AssignButton({ vehicleId, taskId }: Readonly<TaskIdentifier>) {
  const [activateRouteTask] = useActivateRouteTaskMutation();

  const confirm = useConfirm();
  const { placeLoadOptions, placeUnloadOptions, taskTypeOptions } = useRouteTaskData(vehicleId);

  const tasks = useAppSelector((state) => selectMergedVehicleTasks(state, vehicleId));
  const currentTask = useAppSelector((state) => selectMergedVehicleTask(state, vehicleId, taskId));

  const handleAssignTask = async () => {
    const activeTask = tasks.find((i) => ACTIVE_STATUS.has(i.status));
    if (!activeTask || !currentTask?.id) return;

    const activeTaskDescription = formatTaskDescription(activeTask, {
      taskTypeOptions,
      placeLoadOptions,
      placeUnloadOptions,
    });

    const isConfirmed = await confirm({
      title: 'Вы действительно хотите назначить новое задание объекту?',
      message: `Текущее задание ${activeTaskDescription} будет завершено.`,
      confirmText: 'Назначить',
      cancelText: 'Назад к заданиям',
      size: 'md',
    });

    if (!isConfirmed) return;

    try {
      await activateRouteTask({ taskId: currentTask.id, vehicleId: String(vehicleId) }).unwrap();
      toast.success({ message: 'Назначено новое наряд-задание' });
    } catch {
      toast.error({ message: 'Не удалось назначить наряд-задание' });
    }
  };

  return (
    <AppButton
      variant="clear"
      size="xs"
      onClick={handleAssignTask}
    >
      Назначить
    </AppButton>
  );
}
