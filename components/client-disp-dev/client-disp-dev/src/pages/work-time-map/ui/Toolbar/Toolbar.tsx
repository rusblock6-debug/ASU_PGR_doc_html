import { addDays, subDays } from 'date-fns';
import { useMemo } from 'react';

import { ShiftFilter } from '@/features/shift-filter';
import { StatusList } from '@/features/StatusList';
import { VehiclesFilter } from '@/features/vehicles-filter';

import { getShiftsInfo, END_SHIFT_OFFSET } from '@/entities/shift';

import InfoIcon from '@/shared/assets/icons/ic-info.svg?react';
import InfoMinus from '@/shared/assets/icons/ic-minus.svg?react';
import InfoPlus from '@/shared/assets/icons/ic-plus.svg?react';
import ReturnIcon from '@/shared/assets/icons/ic-return.svg?react';
import { useResponsiveOverflow } from '@/shared/lib/hooks/useResponsiveOverflow';
import { useTimezone } from '@/shared/lib/hooks/useTimezone';
import { AppButton } from '@/shared/ui/AppButton';
import { Menu } from '@/shared/ui/Menu';
import { Skeleton } from '@/shared/ui/Skeleton';

import { useWorkTimeMapPageContext } from '../../model/WorkTimeMapPageContext';

import { ITEMS_PRIORITY, ResponsiveToolbar, ResponsiveLabelsLegend } from './ResponsiveToolbar';
import styles from './Toolbar.module.css';

/**
 * Представляет компонент панели управления.
 */
export function Toolbar() {
  const {
    statuses,
    isLoading,
    zoomControlRef,
    vehicles,
    vehiclesFilterState,
    shiftDefinitions,
    dateRangeFilterState: { filterState, onFilterChange },
  } = useWorkTimeMapPageContext();

  const tz = useTimezone();

  const now = tz.getNow();

  const currentShift = useMemo(() => {
    const yesterday = subDays(now, 1);

    const tomorrow = addDays(now, 1);

    return getShiftsInfo([yesterday, now, tomorrow], shiftDefinitions).find(
      (item) => tz.toTimezone(item.endTime).getTime() > now.getTime(),
    );
  }, [now, shiftDefinitions, tz]);

  const isShowGoToCurrentShiftButton = useMemo(() => {
    if (currentShift) {
      const filterFrom = filterState.from.getTime();
      const filterTo = filterState.to.getTime();
      const shiftStart = currentShift.startTime.getTime();
      const shiftEnd = currentShift.endTime.getTime();

      if (filterFrom < shiftEnd && filterTo > shiftStart) {
        return false;
      }
    }

    return true;
  }, [currentShift, filterState]);

  const handleZoomIn = () => {
    zoomControlRef?.current?.zoomIn(2);
  };

  const handleZoomOut = () => {
    zoomControlRef?.current?.zoomOut(2);
  };

  const handleGoToCurrentShift = () => {
    if (currentShift) {
      const endTime = new Date(currentShift.endTime);
      endTime.setTime(endTime.getTime() - END_SHIFT_OFFSET);

      zoomControlRef?.current?.zoomToRange(currentShift.startTime, endTime);
    }
  };

  const onShiftFilterChange = (startDate: Date, endDate: Date) => {
    onFilterChange(startDate, endDate);
    zoomControlRef?.current?.zoomToRange(startDate, endDate);
  };

  const { containerRef, setItemRef, hiddenCount } = useResponsiveOverflow();

  if (isLoading) {
    return (
      <div
        ref={containerRef}
        className={styles.root}
      >
        <Skeleton />
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className={styles.root}
    >
      <div className={styles.filters_container}>
        <div ref={(el) => setItemRef(el, ITEMS_PRIORITY.SHIFT_FILTER)}>
          <ShiftFilter
            shiftDefinitions={shiftDefinitions}
            filterState={filterState}
            onFilterChange={onShiftFilterChange}
            mode="multiShift"
          />
        </div>
        <div ref={(el) => setItemRef(el, ITEMS_PRIORITY.VEHICLES_FILTER)}>
          <VehiclesFilter
            vehicles={vehicles}
            {...vehiclesFilterState}
            selectedVehicleIds={vehiclesFilterState.filterState}
          />
        </div>
      </div>
      <div ref={(el) => setItemRef(el, ITEMS_PRIORITY.TO_CURRENT_SHIFT_BUTTON)}>
        {isShowGoToCurrentShiftButton && (
          <AppButton
            size="s"
            variant="clear"
            rightSection={<ReturnIcon />}
            onClick={handleGoToCurrentShift}
          >
            К текущей смене
          </AppButton>
        )}
      </div>
      <div className={styles.buttons_container}>
        <div className={styles.zoom_buttons_container}>
          <AppButton
            onlyIcon
            variant="clear"
            title="Уменьшить масштаб"
            onClick={handleZoomOut}
          >
            <InfoMinus />
          </AppButton>
          <AppButton
            onlyIcon
            variant="clear"
            title="Увеличить масштаб"
            onClick={handleZoomIn}
          >
            <InfoPlus />
          </AppButton>
        </div>
        <Menu
          width={272}
          closeOnClickOutside
        >
          <Menu.Target>
            <div ref={(el) => setItemRef(el, ITEMS_PRIORITY.LEGEND_BUTTON)}>
              <AppButton
                onlyIcon
                variant="clear"
                title="Легенда обозначений"
              >
                <InfoIcon />
              </AppButton>
            </div>
          </Menu.Target>

          <Menu.Dropdown className={styles.dropdown}>
            <div className={styles.legend_container}>
              <p className={styles.legend_title}>Легенда обозначений</p>
              <StatusList statuses={statuses} />
            </div>
          </Menu.Dropdown>
        </Menu>
      </div>

      {hiddenCount > 0 && (
        <ResponsiveToolbar
          hiddenCount={hiddenCount}
          isShowGoToCurrentShiftButton={isShowGoToCurrentShiftButton}
          shiftFilter={
            <ShiftFilter
              shiftDefinitions={shiftDefinitions}
              filterState={filterState}
              onFilterChange={onShiftFilterChange}
              mode="multiShift"
              withinPortal={false}
            />
          }
          vehiclesFilter={
            <VehiclesFilter
              vehicles={vehicles}
              {...vehiclesFilterState}
              selectedVehicleIds={vehiclesFilterState.filterState}
              withinPortal={false}
            />
          }
          toCurrentShiftButton={
            <div>
              <AppButton
                size="s"
                variant="clear"
                rightSection={<ReturnIcon />}
                onClick={handleGoToCurrentShift}
              >
                К текущей смене
              </AppButton>
            </div>
          }
          legendButton={<ResponsiveLabelsLegend statuses={statuses} />}
        />
      )}
    </div>
  );
}
