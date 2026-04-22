import { useEffect, useMemo } from 'react';

import { ShiftFilter } from '@/features/shift-filter';

import { END_SHIFT_OFFSET, getShiftByDate } from '@/entities/shift';

import { useGetAllWorkRegimesQuery } from '@/shared/api/endpoints/work-regimes';
import PlayIcon from '@/shared/assets/icons/ic-play.svg?react';
import { EMPTY_ARRAY } from '@/shared/lib/constants';
import { useAppDispatch } from '@/shared/lib/hooks/useAppDispatch';
import { useAppSelector } from '@/shared/lib/hooks/useAppSelector';
import { AppButton } from '@/shared/ui/AppButton';

import {
  selectHistoryRangeFilter,
  selectSelectedVehicleHistoryIds,
  selectIsVisibleHistoryPlayer,
} from '../../../model/selectors';
import { mapActions } from '../../../model/slice';
import { LayersSection } from '../LayersSection';
import { ObjectsPanel } from '../ObjectsPanel';

import styles from './HistoryModeContent.module.css';

/**
 * Контент режима «История» — панель объектов и панель слоёв.
 */
export function HistoryModeContent() {
  const dispatch = useAppDispatch();
  const dateRangeFilter = useAppSelector(selectHistoryRangeFilter);
  const isVisibleHistoryPlayer = useAppSelector(selectIsVisibleHistoryPlayer);
  const { data: workRegimesData } = useGetAllWorkRegimesQuery();

  const shiftDefinitions = useMemo(
    () => workRegimesData?.items.at(0)?.shifts_definition ?? EMPTY_ARRAY,
    [workRegimesData?.items],
  );

  const selectedVehicleHistoryIds = useAppSelector(selectSelectedVehicleHistoryIds);

  useEffect(() => {
    if (!dateRangeFilter && shiftDefinitions.length > 0) {
      const currentShift = getShiftByDate(new Date(), shiftDefinitions);

      if (currentShift) {
        const endDateWithCorrection = new Date(currentShift.endTime.getTime() - END_SHIFT_OFFSET);
        const filter = { from: currentShift.startTime.toISOString(), to: endDateWithCorrection.toISOString() };

        dispatch(mapActions.setHistoryRangeFilter(filter));
      }
    }
  }, [dateRangeFilter, dispatch, shiftDefinitions]);

  const onDateRangeFilterChange = (startDate: Date, endDate: Date) => {
    const filter = { from: startDate.toISOString(), to: endDate.toISOString() };
    dispatch(mapActions.setHistoryRangeFilter(filter));
  };

  const handlePlay = () => {
    if (dateRangeFilter) {
      dispatch(mapActions.toggleVisibleHistoryPlayer(true));
      dispatch(mapActions.setPlayerCurrentTime(new Date(dateRangeFilter.from).getTime()));
    }
  };

  return (
    <>
      <div className={styles.toolbar}>
        <div className={styles.shift_filter_container}>
          <ShiftFilter
            shiftDefinitions={shiftDefinitions}
            filterState={
              dateRangeFilter ? { from: new Date(dateRangeFilter.from), to: new Date(dateRangeFilter.to) } : undefined
            }
            onFilterChange={onDateRangeFilterChange}
            mode="multiShift"
            withCurrentShift
            disabled={isVisibleHistoryPlayer}
          />
        </div>
        {!isVisibleHistoryPlayer && (
          <AppButton
            onlyIcon
            size="xs"
            disabled={selectedVehicleHistoryIds.length === 0}
            onClick={handlePlay}
          >
            <PlayIcon />
          </AppButton>
        )}
      </div>
      <ObjectsPanel />
      <LayersSection />
    </>
  );
}
