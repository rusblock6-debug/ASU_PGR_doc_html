import { skipToken } from '@reduxjs/toolkit/query';
import { useEffect, useMemo, useState } from 'react';

import { type DateRangeFilter, useDateRangeFilter } from '@/features/shift-filter';

import { MSK_CORRECTION_OFFSET } from '@/entities/shift';

import {
  type StateHistory,
  useGetAllStateHistoryQuery,
  useLazyGetAllStateHistoryQuery,
} from '@/shared/api/endpoints/state-history';
import {
  isStreamStateHistoryChangedMessage,
  isStreamStateTransitionMessage,
  useGetStreamAllQuery,
} from '@/shared/api/endpoints/streams';
import type { ShiftDefinition } from '@/shared/api/endpoints/work-regimes';
import { EMPTY_ARRAY } from '@/shared/lib/constants';
import { useIsMounted } from '@/shared/lib/hooks/useIsMounted';

/**
 * Представляет хук источника данных для истории статусов оборудования.
 *
 * @param dateRangeFilter значение фильтра по диапазону дат.
 * @param vehicleIdsSet список идентификаторов оборудования по которым нужно выполнить фильтрацию.
 * @param shiftDefinitions определение смен работы предприятия.
 * @param isFullShift признак запроса полносменных статусов.
 */
export function useStateHistoryDataSource(
  dateRangeFilter: DateRangeFilter,
  vehicleIdsSet: Set<number>,
  shiftDefinitions: readonly ShiftDefinition[],
  isFullShift: boolean,
) {
  const isMounted = useIsMounted();

  const [stateHistory, setStateHistory] = useState<readonly StateHistory[]>(EMPTY_ARRAY);

  const { data: stateHistoryStreamData } = useGetStreamAllQuery(undefined, {
    skip: !isMounted,
    refetchOnMountOrArgChange: true,
  });

  const vehicleIds = useMemo(() => Array.from(vehicleIdsSet), [vehicleIdsSet]);

  const dateFilter = useDateRangeFilter(dateRangeFilter, shiftDefinitions);

  const {
    data: stateHistoryData,
    isLoading: isLoadingAllStateHistory,
    isFetching: isFetchingAllStateHistory,
  } = useGetAllStateHistoryQuery(dateFilter ? { ...dateFilter, vehicleIds, isFullShift } : skipToken, {
    refetchOnFocus: true,
    refetchOnMountOrArgChange: true,
    skip: !dateFilter,
  });

  const [fetchShiftHistoryByVehicleId] = useLazyGetAllStateHistoryQuery();

  useEffect(() => {
    if (stateHistoryData) {
      setStateHistory(stateHistoryData.items);
    }
  }, [stateHistoryData]);

  useEffect(() => {
    if (stateHistoryStreamData && isStreamStateTransitionMessage(stateHistoryStreamData) && !isFullShift) {
      const stateMs = new Date(stateHistoryStreamData.timestamp).getTime();
      const fromMs = dateRangeFilter.from.getTime();
      const toMs = dateRangeFilter.to.getTime();
      if (vehicleIdsSet.size > 0 && !vehicleIdsSet.has(stateHistoryStreamData.vehicle_id)) {
        return;
      }

      if (stateMs < fromMs || stateMs >= toMs) {
        return;
      }

      setStateHistory((prevState) => [...prevState, stateHistoryStreamData]);
    }
  }, [dateRangeFilter.from, dateRangeFilter.to, isFullShift, stateHistoryStreamData, vehicleIdsSet]);

  useEffect(() => {
    const fn = async () => {
      if (stateHistoryStreamData && isStreamStateHistoryChangedMessage(stateHistoryStreamData)) {
        const { shift_date: shiftDate, shift_num: shiftNum, vehicle_id: vehicleId } = stateHistoryStreamData;

        const shiftConfig = shiftDefinitions.find((item) => item.shift_num === shiftNum);
        if (!shiftConfig) {
          return;
        }

        if (vehicleIdsSet.size > 0 && !vehicleIdsSet.has(vehicleId)) {
          return;
        }

        const response = await fetchShiftHistoryByVehicleId({
          fromDate: shiftDate,
          toDate: shiftDate,
          fromShiftNum: shiftNum,
          toShiftNum: shiftNum,
          vehicleIds: [vehicleId],
          isFullShift,
        });

        const baseMs = new Date(shiftDate).getTime();

        const shiftStartMs = baseMs + (shiftConfig.start_time_offset - MSK_CORRECTION_OFFSET) * 1000;
        const shiftEndMs = baseMs + (shiftConfig.end_time_offset - MSK_CORRECTION_OFFSET) * 1000;

        const filterState = (item: StateHistory) => !isStateInShift(item, vehicleId, shiftStartMs, shiftEndMs);

        setStateHistory((prevState) => {
          const filteredState = prevState.filter(filterState);
          return [...filteredState, ...(response.data?.items ?? [])];
        });
      }
    };

    void fn();
  }, [fetchShiftHistoryByVehicleId, stateHistoryStreamData, shiftDefinitions, vehicleIdsSet, isFullShift]);

  return useMemo(
    () => ({ stateHistory, isLoadingAllStateHistory: isLoadingAllStateHistory || isFetchingAllStateHistory }),
    [isLoadingAllStateHistory, isFetchingAllStateHistory, stateHistory],
  );
}

function isStateInShift(state: StateHistory, vehicleId: number, shiftStartMs: number, shiftEndMs: number) {
  if (state.vehicle_id !== vehicleId) {
    return false;
  }

  const stateTimeMs = new Date(state.timestamp).getTime();

  return stateTimeMs >= shiftStartMs && stateTimeMs < shiftEndMs;
}
