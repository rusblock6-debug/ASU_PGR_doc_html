import { type ReactNode, useState } from 'react';

import { Popover } from '@/shared/ui/Popover';
import { ResponsiveMenuButton } from '@/shared/ui/ResponsiveMenuButton';

import styles from './ResponsiveToolbar.module.css';

/** Приоритеты отображения для элементов панели управления. */
export const ITEMS_PRIORITY = {
  SHIFT_FILTER: 0,
  VEHICLES_FILTER: 1,
  TO_CURRENT_SHIFT_BUTTON: 2,
  LEGEND_BUTTON: 3,
} as const;

/**
 * Представляет свойства компонента адаптивного меню панели управления на странице "Карта рабочего времени".
 */
interface ResponsiveToolbarProps {
  /** Возвращает количество скрытых элементов. */
  readonly hiddenCount: number;
  /** Возвращает признак для отображения кнопки "К текущей смене". */
  readonly isShowGoToCurrentShiftButton: boolean;
  /** Возвращает компонент фильтра оборудования. */
  readonly vehiclesFilter: ReactNode;
  /** Возвращает компонент фильтра смен. */
  readonly shiftFilter: ReactNode;
  /** Возвращает компонент фильтра смен. */
  readonly toCurrentShiftButton: ReactNode;
  /** Возвращает компонент фильтра смен. */
  readonly legendButton: ReactNode;
}

/**
 * Представляет компонент адаптивного меню панели управления на странице "Карта рабочего времени".
 */
export function ResponsiveToolbar(props: ResponsiveToolbarProps) {
  const { hiddenCount, isShowGoToCurrentShiftButton, vehiclesFilter, shiftFilter, toCurrentShiftButton, legendButton } =
    props;

  const [opened, setOpened] = useState(false);

  return (
    <Popover
      onChange={setOpened}
      offset={2}
      position="bottom-end"
    >
      <Popover.Target>
        <div>
          <ResponsiveMenuButton opened={opened} />
        </div>
      </Popover.Target>
      <Popover.Dropdown classNames={{ dropdown: styles.dropdown }}>
        {hiddenCount > ITEMS_PRIORITY.VEHICLES_FILTER && vehiclesFilter}
        {hiddenCount > ITEMS_PRIORITY.SHIFT_FILTER && shiftFilter}
        {hiddenCount > ITEMS_PRIORITY.LEGEND_BUTTON && legendButton}
        {hiddenCount > ITEMS_PRIORITY.TO_CURRENT_SHIFT_BUTTON && isShowGoToCurrentShiftButton && toCurrentShiftButton}
      </Popover.Dropdown>
    </Popover>
  );
}
