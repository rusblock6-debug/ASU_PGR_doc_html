import type { SubscriptionOptions } from '@reduxjs/toolkit/query';

import { useGetShiftTasksQuery } from '@/shared/api';
import { VEHICLE_ID_NUM } from '@/shared/config/env';

/** Опции подписки useQuery (refetchOnMountOrArgChange и др.). */
type ShiftTasksSubscriptionOptions = SubscriptionOptions & {
  readonly skip?: boolean;
  readonly refetchOnMountOrArgChange?: boolean | number;
};

/**
 * Возвращает дату текущего дня в формате YYYY-MM-DD.
 */
const getTodayShiftDate = () => {
  const d = new Date();
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
};

/**
 * Хук получения заданий текущей смены для настроенного ТС.
 */
export const useCurrentShiftTasks = (subscriptionOptions?: ShiftTasksSubscriptionOptions) => {
  const shiftDate = getTodayShiftDate();

  return useGetShiftTasksQuery(
    {
      vehicle_ids: [VEHICLE_ID_NUM],
      shift_date: shiftDate,
      size: 100,
      page: 1,
    },
    subscriptionOptions,
  );
};
