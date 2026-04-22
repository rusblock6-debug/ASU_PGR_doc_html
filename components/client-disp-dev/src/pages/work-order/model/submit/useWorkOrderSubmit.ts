import { useState } from 'react';

import { useLazyGetShiftTasksListQuery, useUpsertShiftTasksMutation } from '@/shared/api/endpoints/shift-tasks';
import { hasValue } from '@/shared/lib/has-value';
import { useAppDispatch } from '@/shared/lib/hooks/useAppDispatch';
import { useAppStore } from '@/shared/lib/hooks/useAppStore';
import { ruPlural } from '@/shared/lib/plural';
import { toast } from '@/shared/ui/Toast';

import {
  selectAllChangedVehicleIds,
  selectAllServerShiftTasks,
  selectCurrentShift,
  selectFilteredVehicleIds,
  selectSelectedStatus,
} from '../selectors';
import { workOrderActions } from '../slice';

import { buildApiItems } from './build-api-items';
import { validateChangedTasks } from './validation';

/**
 * Представляет параметры для хука useWorkOrderSubmit.
 */
interface UseWorkOrderSubmitParams {
  /** Перезапрашивает наряд-задания с сервера после успешной отправки. */
  readonly refetch: () => Promise<unknown>;
}

/**
 * Хук для отправки наряд-заданий.
 *
 * Логика отправки:
 * 1. Валидация изменённых задач → ошибки сохраняются в redux store.
 * 2. Отправка только валидных машин на сервер. При отправке игнорируем Server-Sent Events.
 * 3. Получение свежих данных от сервера → очистка локальных изменений в redux store (created/modified/deleted).
 */
export function useWorkOrderSubmit({ refetch }: UseWorkOrderSubmitParams) {
  const store = useAppStore();
  const dispatch = useAppDispatch();

  const [upsertShiftTasks] = useUpsertShiftTasksMutation();
  const [fetchUnfilteredTasks] = useLazyGetShiftTasksListQuery();

  const [isSubmitting, setIsSubmitting] = useState(false);

  const submit = async () => {
    const state = store.getState();
    const vehicleIds = selectFilteredVehicleIds(state);
    const dirtyVehicleIds = selectAllChangedVehicleIds(state);
    const selectedStatus = selectSelectedStatus(state);
    const currentShift = selectCurrentShift(state);

    if (!hasValue(currentShift)) return;

    const dirtySet = new Set(dirtyVehicleIds);
    const changedVehicleIds = vehicleIds.filter((id) => dirtySet.has(id));
    if (changedVehicleIds.length === 0) return;

    setIsSubmitting(true);

    try {
      // При активном фильтре по статусу RTK-кеш содержит только отфильтрованные route_tasks (маршрутные задания для транспорта).
      // Запрашиваем все данные, чтобы массовая отправка не удалила задания скрытые фильтром.
      let serverShiftTasks = selectAllServerShiftTasks(state);

      if (selectedStatus !== 'all') {
        try {
          const result = await fetchUnfilteredTasks({
            shift_date: currentShift.shiftDate,
            shift_num: currentShift.shiftNum,
            vehicle_ids: [...changedVehicleIds],
          }).unwrap();
          serverShiftTasks = result.items;
        } catch {
          toast.error({ message: 'Не удалось загрузить все данные для сохранения' });
          return;
        }
      }

      const { created, modified, deleted } = store.getState().workOrder;
      const edits = { created, modified, deleted };

      const { errors, invalidVehicleIds } = validateChangedTasks(edits, serverShiftTasks, changedVehicleIds);
      if (Object.keys(errors).length > 0) {
        dispatch(workOrderActions.setValidationErrors(errors));
      }
      const invalidVehicleCount = invalidVehicleIds.size;
      if (invalidVehicleCount > 0) {
        toast.error({
          message: `Наряд-задания не отправлены ${invalidVehicleCount} ${ruPlural(invalidVehicleCount, 'объекту', 'объектам', 'объектам')}`,
        });
      }

      const validVehicleIds = changedVehicleIds.filter((id) => !invalidVehicleIds.has(id));
      if (validVehicleIds.length === 0) return;

      const { items } = buildApiItems(validVehicleIds, edits, serverShiftTasks, currentShift);
      if (items.length === 0) return;

      await upsertShiftTasks({ items }).unwrap();
      await refetch();

      const submittedVehicleIds = items.map((item) => item.vehicle_id).filter(hasValue);
      dispatch(workOrderActions.clearSubmittedEdits({ vehicleIds: submittedVehicleIds }));

      toast.success({
        message: `Наряд-задания отправлены: ${validVehicleIds.length} ${ruPlural(validVehicleIds.length, 'объекту', 'объектам', 'объектам')}`,
      });
    } catch {
      toast.error({ message: 'Ошибка отправки наряд-задания' });
    } finally {
      setIsSubmitting(false);
    }
  };

  return { submit, isSubmitting };
}
