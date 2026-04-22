import { useCancelRouteTaskMutation } from '@/shared/api/endpoints/route-tasks';
import { useConfirm } from '@/shared/lib/confirm';
import { useAppSelector } from '@/shared/lib/hooks/useAppSelector';
import { AppButton } from '@/shared/ui/AppButton';
import { toast } from '@/shared/ui/Toast';

import { formatTaskDescription } from '../../lib/format-task-description';
import { useRouteTaskData } from '../../lib/hooks/useRouteTaskData';
import { selectMergedVehicleTask } from '../../model/selectors';
import type { TaskIdentifier } from '../../model/types';

/**
 * Кнопка отмены маршрутного задания с подтверждением.
 * Показывает диалог подтверждения с деталями задания перед отменой.
 * При подтверждении отменяет задание и показывает уведомление.
 */
export function CancelButton({ vehicleId, taskId }: Readonly<TaskIdentifier>) {
  const [cancelRouteTask] = useCancelRouteTaskMutation();

  const confirm = useConfirm();
  const { placeLoadOptions, placeUnloadOptions, taskTypeOptions } = useRouteTaskData(vehicleId);

  const task = useAppSelector((state) => selectMergedVehicleTask(state, vehicleId, taskId));

  const handleCancelTask = async () => {
    if (!task) return;

    const taskDescription = formatTaskDescription(task, {
      taskTypeOptions,
      placeLoadOptions,
      placeUnloadOptions,
    });

    const isConfirmed = await confirm({
      title: 'Вы действительно хотите отменить задание?',
      message: `Задание ${taskDescription} будет отменено.`,
      confirmText: 'Отменить',
      cancelText: 'Назад к заданиям',
      size: 'md',
    });

    if (!isConfirmed) return;

    try {
      await cancelRouteTask({ taskId: task.id, vehicleId: String(vehicleId) }).unwrap();
      toast.success({ message: 'Наряд-задание отменено' });
    } catch {
      toast.error({ message: 'Не удалось отменить задание' });
    }
  };

  return (
    <AppButton
      variant="clear"
      size="xs"
      onClick={handleCancelTask}
    >
      Отменить
    </AppButton>
  );
}
