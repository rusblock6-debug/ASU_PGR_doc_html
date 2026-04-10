import { subDays, addDays } from 'date-fns';
import { useCallback, useMemo } from 'react';

import { getShiftsInfo } from '@/entities/shift';

import type { ShiftDefinition } from '@/shared/api/endpoints/work-regimes';

import type { DateRangeFilter } from '../date-range-filter';

/**
 * Хук фильтра по диапазону дат.
 *
 * @param filterState состояние фильтра.
 * @param shiftDefinitions определение смен работы предприятия.
 */
export function useDateRangeFilter(filterState: DateRangeFilter, shiftDefinitions: readonly ShiftDefinition[]) {
  const { from: fromDate, to: toDate } = filterState;

  const getShiftFilterValue = useCallback(
    (date: Date) => {
      const yesterday = subDays(date, 1);

      const tomorrow = addDays(date, 1);

      const shifts = getShiftsInfo([yesterday, date, tomorrow], shiftDefinitions);

      for (const shift of shifts) {
        if (shift.startTime.getTime() <= date.getTime() && shift.endTime.getTime() > date.getTime()) {
          return {
            shiftDate: shift.shiftDate.toISOString().split('T')[0],
            shiftNum: shift.shiftNum,
          };
        }
      }

      return null;
    },
    [shiftDefinitions],
  );

  const from = useMemo(() => getShiftFilterValue(fromDate), [fromDate, getShiftFilterValue]);

  const to = useMemo(() => getShiftFilterValue(toDate), [toDate, getShiftFilterValue]);

  return useMemo(() => {
    if (!from || !to) {
      return null;
    }

    return {
      fromDate: from.shiftDate,
      toDate: to.shiftDate,
      fromShiftNum: from.shiftNum,
      toShiftNum: to.shiftNum,
    };
  }, [from, to]);
}
