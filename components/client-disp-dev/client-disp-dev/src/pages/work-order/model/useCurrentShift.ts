import { useCallback, useEffect, useMemo } from 'react';

import type { DateRangeFilter } from '@/features/shift-filter';

import { END_SHIFT_OFFSET, getShiftByDate, getShiftsInfo } from '@/entities/shift';

import { useGetAllWorkRegimesQuery } from '@/shared/api/endpoints/work-regimes';
import { EMPTY_ARRAY } from '@/shared/lib/constants';
import { hasValue } from '@/shared/lib/has-value';
import { useAppDispatch } from '@/shared/lib/hooks/useAppDispatch';
import { useAppSelector } from '@/shared/lib/hooks/useAppSelector';
import { useTimezone } from '@/shared/lib/hooks/useTimezone';

import { selectCurrentShift } from './selectors';
import { workOrderActions } from './slice';

/**
 * Единый хук для работы с текущей сменой на странице «Наряд-задание»:
 * инициализация при монтировании, диапазон для фильтра, переключение смены.
 *
 * @returns
 * - `isShiftReady` true, когда смена определена и записана в redux;
 * - `shiftDefinitions`, `filterState` для ShiftFilter;
 * - `changeShift` переключить смену по дате;
 * - `currentShift` текущая смена.
 */
export function useCurrentShift() {
  const dispatch = useAppDispatch();
  const tz = useTimezone();

  const { data: workRegimesData } = useGetAllWorkRegimesQuery();
  const workRegime = workRegimesData?.items.at(0);
  const shiftDefinitions = workRegime?.shifts_definition ?? EMPTY_ARRAY;

  const currentShift = useAppSelector(selectCurrentShift);
  const isShiftReady = hasValue(currentShift);

  useEffect(() => {
    if (isShiftReady || shiftDefinitions.length === 0 || !workRegime) return;

    const shiftInfo = getShiftByDate(new Date(), shiftDefinitions);
    if (!shiftInfo) return;

    dispatch(
      workOrderActions.setCurrentShift({
        shiftDate: tz.format(shiftInfo.shiftDate, 'yyyy-MM-dd'),
        shiftNum: shiftInfo.shiftNum,
        workRegimeId: workRegime.id,
      }),
    );
  }, [isShiftReady, shiftDefinitions, workRegime, dispatch, tz]);

  const filterState = useMemo<DateRangeFilter>(() => {
    if (!currentShift) return { from: new Date(), to: new Date() };

    const shiftDate = new Date(currentShift.shiftDate + 'T00:00:00Z');
    const shiftInfo = getShiftsInfo([shiftDate], shiftDefinitions).find(
      (shift) => shift.shiftNum === currentShift.shiftNum,
    );

    return shiftInfo
      ? {
          from: shiftInfo.startTime,
          to: new Date(shiftInfo.endTime.getTime() - END_SHIFT_OFFSET),
        }
      : { from: new Date(), to: new Date() };
  }, [currentShift, shiftDefinitions]);

  const changeShift = useCallback(
    (startDate: Date) => {
      const shiftInfo = getShiftByDate(startDate, shiftDefinitions);
      if (!shiftInfo || !workRegime) return;

      dispatch(
        workOrderActions.setCurrentShift({
          shiftDate: tz.format(shiftInfo.shiftDate, 'yyyy-MM-dd'),
          shiftNum: shiftInfo.shiftNum,
          workRegimeId: workRegime.id,
        }),
      );
    },
    [shiftDefinitions, workRegime, dispatch, tz],
  );

  return {
    isShiftReady,
    shiftDefinitions,
    filterState,
    changeShift,
    currentShift,
  };
}
