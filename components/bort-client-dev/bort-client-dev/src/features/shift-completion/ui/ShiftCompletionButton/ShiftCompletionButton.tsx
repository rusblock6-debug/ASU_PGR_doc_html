import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { useClearActiveTaskMutation } from '@/shared/api';
import type { ShiftTaskResponse } from '@/shared/api/types/trip-service';
import { getRouteSessionEnded } from '@/shared/routes/router';
import { AppButton } from '@/shared/ui/AppButton';
import { ConfirmModal } from '@/shared/ui/ConfirmModal';

import { buildShiftSummary } from '../../model/shift-summary';

/**
 * Пропсы кнопки завершения смены.
 */
interface ShiftCompletionButtonProps {
  readonly shift: ShiftTaskResponse | null;
}

/**
 * Завершение смены: сводка и выход (очистка активного задания + переход на заглушку).
 */
export const ShiftCompletionButton = ({ shift }: ShiftCompletionButtonProps) => {
  const [open, setOpen] = useState(false);
  const navigate = useNavigate();
  const [clearActive, { isLoading }] = useClearActiveTaskMutation();
  const tasks = shift?.route_tasks ?? [];
  const summary = buildShiftSummary(tasks);

  const message = [
    `Маршрутов: ${summary.routesCount}`,
    `Рейсов (факт / план): ${summary.actualTrips} / ${summary.plannedTrips}`,
    `Объём, м³: ${summary.volume.toFixed(1)}`,
    `Вес, т: ${summary.weight.toFixed(1)}`,
    'Выйти из смены?',
  ].join('\n');

  const handleConfirm = async () => {
    try {
      await clearActive().unwrap();
    } catch {
      /* очистка может быть недоступна без бэкенда */
    }
    setOpen(false);
    void navigate(getRouteSessionEnded());
  };

  return (
    <>
      <AppButton
        variant="secondary"
        onClick={() => setOpen(true)}
      >
        Завершить смену
      </AppButton>
      <ConfirmModal
        isOpen={open}
        title="Итоги смены"
        message={message}
        closeButtonText="Отмена"
        confirmButtonText="Выйти"
        isLoading={isLoading}
        onClose={() => setOpen(false)}
        onConfirm={() => void handleConfirm()}
        size="md"
      />
    </>
  );
};
