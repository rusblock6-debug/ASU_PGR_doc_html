import { useNavigate } from 'react-router-dom';

import type { ShiftTaskResponse } from '@/shared/api/endpoints/shift-tasks';
import { useClearActiveTaskMutation } from '@/shared/api/endpoints/tasks';
import { useConfirm } from '@/shared/lib/confirm';
import { getRouteSessionEnded } from '@/shared/routes/router';
import { AppButton } from '@/shared/ui/AppButton';

import { buildShiftSummary } from '../../model/shift-summary';

/**
 * Пропсы кнопки завершения смены.
 */
interface ShiftCompletionButtonProps {
  /** Текущая задача смены; `null` — смена не загружена. */
  readonly shift: ShiftTaskResponse | null;
}

/**
 * Завершение смены: сводка и выход (очистка активного задания + переход на заглушку).
 */
export const ShiftCompletionButton = ({ shift }: ShiftCompletionButtonProps) => {
  const navigate = useNavigate();
  const confirm = useConfirm();
  const [clearActive] = useClearActiveTaskMutation();
  const tasks = shift?.route_tasks ?? [];
  const summary = buildShiftSummary(tasks);

  const handleClick = async () => {
    const message = [
      `Маршрутов: ${summary.routesCount}`,
      `Рейсов (факт / план): ${summary.actualTrips} / ${summary.plannedTrips}`,
      `Объём, м³: ${summary.volume.toFixed(1)}`,
      `Вес, т: ${summary.weight.toFixed(1)}`,
      'Выйти из смены?',
    ].join('\n');

    const confirmed = await confirm({
      title: 'Итоги смены',
      message,
      confirmText: 'Выйти',
      cancelText: 'Отмена',
      size: 'md',
    });

    if (!confirmed) return;

    try {
      await clearActive().unwrap();
    } catch {
      /* очистка может быть недоступна без бэкенда */
    }
    void navigate(getRouteSessionEnded());
  };

  return (
    <AppButton
      variant="secondary"
      onClick={() => void handleClick()}
    >
      Завершить смену
    </AppButton>
  );
};
