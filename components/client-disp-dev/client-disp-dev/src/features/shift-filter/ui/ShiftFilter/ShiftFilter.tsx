import type { MenuProps } from '@mantine/core';
import { subDays } from 'date-fns';
import { useEffect, useMemo, useState } from 'react';

import {
  END_SHIFT_OFFSET,
  getShiftByDate,
  getShiftsInfo,
  MSK_CORRECTION_OFFSET,
  type ShiftInfo,
} from '@/entities/shift';

import type { ShiftDefinition } from '@/shared/api/endpoints/work-regimes';
import ArrowDownIcon from '@/shared/assets/icons/ic-arrow-down.svg?react';
import { hasValue } from '@/shared/lib/has-value';
import { useCheckTextOverflow } from '@/shared/lib/hooks/useCheckTextOverflow';
import { useTimezone } from '@/shared/lib/hooks/useTimezone';
import { formatInTimezone } from '@/shared/lib/timezone';
import { Menu } from '@/shared/ui/Menu';
import { MenuTargetButton } from '@/shared/ui/MenuTargetButton';
import { Radio } from '@/shared/ui/Radio';
import { Tooltip } from '@/shared/ui/Tooltip';

import type { DateRangeFilter } from '../../model/date-range-filter';
import { ShiftCalendar } from '../ShiftCalendar';

import styles from './ShiftFilter.module.css';

/**
 * Представляет свойства компонента фильтра по сменам.
 */
interface ShiftFilterProps extends Pick<MenuProps, 'position' | 'offset' | 'withinPortal'> {
  /** Возвращает список смен в режиме работы предприятия. */
  readonly shiftDefinitions: readonly ShiftDefinition[];
  /** Возвращает состояние фильтра. */
  readonly filterState?: DateRangeFilter;
  /** Возвращает делегат, вызываемый при изменении состояния фильтра. */
  readonly onFilterChange: (startDate: Date, endDate: Date) => void;
  /** Возвращает режим фильтра. */
  readonly mode?: 'singleShift' | 'multiShift';
  /** Возвращает признак необходимости отображения текущей смены в быстрых фильтрах. */
  readonly withCurrentShift?: boolean;
}

/**
 * Представляет компонент фильтра по сменам.
 */
export function ShiftFilter(props: ShiftFilterProps) {
  const {
    shiftDefinitions,
    filterState,
    onFilterChange,
    mode = 'singleShift',
    withCurrentShift,
    position,
    offset,
    withinPortal,
  } = props;

  const tz = useTimezone();

  const now = tz.getNow();

  const [opened, setOpened] = useState(false);

  const [fastFilterValue, setFastFilterValue] = useState<string | null>(null);

  useEffect(() => {
    if (!filterState) {
      return;
    }

    const start = getShiftByDate(filterState.from, shiftDefinitions);
    const end = getShiftByDate(filterState.to, shiftDefinitions);

    if (start && end) {
      setFastFilterValue(getFastFilterValue(start, end));
    }
  }, [filterState, shiftDefinitions]);

  const onChange = (value: string) => {
    const values = value.split('_');

    const date = values.at(0);
    const shiftNum = Number(values.at(1));

    const shiftDefinition = shiftDefinitions.find((item) => item.shift_num === shiftNum);

    if (hasValue(date) && hasValue(shiftNum) && shiftDefinition) {
      const [year, month, day] = date.split('-').map(Number);

      const baseMs = Date.UTC(year, month - 1, day);

      const shiftStart = new Date(baseMs + (shiftDefinition.start_time_offset - MSK_CORRECTION_OFFSET) * 1000);
      const shiftEnd = new Date(
        baseMs + (shiftDefinition.end_time_offset - MSK_CORRECTION_OFFSET) * 1000 - END_SHIFT_OFFSET,
      );

      onFilterChange(shiftStart, shiftEnd);
      setOpened(false);
    }
  };

  const pastShifts = useMemo<readonly ShiftInfo[]>(() => {
    const yesterday = subDays(now, 1);

    const toDaysAgo = subDays(now, 2);

    return getShiftsInfo([toDaysAgo, yesterday, now], shiftDefinitions)
      .filter((item) =>
        withCurrentShift
          ? tz.toTimezone(item.startTime).getTime() <= now.getTime()
          : tz.toTimezone(item.endTime).getTime() < now.getTime(),
      )
      .reverse();
  }, [now, shiftDefinitions, withCurrentShift, tz]);

  const displayText = useMemo(() => {
    if (!filterState) {
      return 'Выберите диапазон смен';
    }

    const start = getShiftByDate(filterState.from, shiftDefinitions);
    const end = getShiftByDate(filterState.to, shiftDefinitions);

    if (!start || !end) {
      return 'Выберите диапазон смен';
    }

    const startFilerDisplayValue = `${tz.format(start.shiftDate, 'dd.MM.yyyy')} (Смена ${start.shiftNum}, ${tz.format(start.startTime, 'HH:mm')} - ${tz.format(start.endTime, 'HH:mm')})`;
    const endFilerDisplayValue = `${tz.format(end.shiftDate, 'dd.MM.yyyy')} (Смена ${end.shiftNum}, ${tz.format(end.startTime, 'HH:mm')} - ${tz.format(end.endTime, 'HH:mm')})`;

    if (start.shiftDate.getTime() === end.shiftDate.getTime() && start.shiftNum === end.shiftNum) {
      return startFilerDisplayValue;
    }

    return `${startFilerDisplayValue} - ${endFilerDisplayValue}`;
  }, [filterState, shiftDefinitions, tz]);

  const { ref, isTextOverflowed } = useCheckTextOverflow(displayText);

  return (
    <Menu
      onChange={setOpened}
      opened={opened}
      closeOnClickOutside
      width="target"
      position={position}
      offset={offset}
      withinPortal={withinPortal}
    >
      <Menu.Target>
        <Tooltip
          label={displayText}
          disabled={!isTextOverflowed}
        >
          <div>
            <MenuTargetButton
              opened={opened}
              label={
                <p
                  ref={ref}
                  className={styles.target_label}
                >
                  {displayText}
                </p>
              }
              rootClassName={styles.target}
            />
          </div>
        </Tooltip>
      </Menu.Target>

      <Menu.Dropdown>
        <div className={styles.dropdown}>
          <Radio.Group
            value={fastFilterValue}
            onChange={onChange}
          >
            <div className={styles.radio_group_container}>
              {pastShifts.map((item) => (
                <Radio
                  key={item.startTime.toISOString()}
                  size="xs"
                  label={`${formatInTimezone(item.shiftDate, null, 'dd.MM.yyyy')} (Смена ${item.shiftNum}, ${tz.format(item.startTime, 'HH:mm')}–${tz.format(item.endTime, 'HH:mm')})`}
                  value={getFastFilterValue(item, item)}
                  classNames={{ labelWrapper: styles.radio_label_wrapper, label: styles.radio_label }}
                />
              ))}
            </div>
          </Radio.Group>
          <Menu.Sub
            offset={11}
            closeDelay={3000}
          >
            <Menu.Sub.Target>
              <Menu.Sub.Item rightSection={<ArrowDownIcon className={styles.sub_menu_arrow} />}>
                Другая дата
              </Menu.Sub.Item>
            </Menu.Sub.Target>

            <Menu.Sub.Dropdown>
              <ShiftCalendar
                shiftDefinitions={shiftDefinitions}
                onFilterChange={(start, end) => {
                  onFilterChange(start, end);
                  setOpened(false);
                }}
                mode={mode}
              />
            </Menu.Sub.Dropdown>
          </Menu.Sub>
        </div>
      </Menu.Dropdown>
    </Menu>
  );
}

/** Возвращает значение "быстрого" фильтра. */
function getFastFilterValue(shiftStartInfo: ShiftInfo, shiftEndInfo: ShiftInfo) {
  return `${shiftStartInfo.shiftDate.toISOString().split('T')[0]}_${shiftStartInfo.shiftNum}_${shiftEndInfo.shiftDate.toISOString().split('T')[0]}_${shiftEndInfo.shiftNum}`;
}
