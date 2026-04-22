import { type ReactNode, useState } from 'react';

import { Popover } from '@/shared/ui/Popover';
import { ResponsiveMenuButton } from '@/shared/ui/ResponsiveMenuButton';

import styles from './ResponsiveToolbar.module.css';

/** Приоритеты отображения для элементов панели управления. */
export const ITEMS_PRIORITY = {
  SHIFT_FILTER: 0,
  VEHICLES_FILTER: 1,
  TASK_STATUS_FILTER: 2,
  ACTION_BUTTONS: 3,
  PLANNED_COUNT: 4,
  SUBMIT_BUTTON: 5,
} as const;

/**
 * Представляет свойства компонента адаптивного меню панели управления на странице "Наряд-задания".
 */
interface ResponsiveToolbarProps {
  /** Возвращает количество скрытых элементов. */
  readonly hiddenCount: number;
  /** Возвращает компонент планируемого объема. */
  readonly planedCount: ReactNode;
  /** Возвращает компонент кнопки "Очистить все". */
  readonly clearButton: ReactNode;
  /** Возвращает компонент кнопки "Скопировать из предыдущей смены". */
  readonly copyButton: ReactNode;
  /** Возвращает компонент кнопки "Отправить". */
  readonly submitButton: ReactNode;
  /** Возвращает компонент фильтра статусов заданий. */
  readonly taskStatusFilter: ReactNode;
  /** Возвращает компонент фильтра оборудования. */
  readonly vehiclesFilter: ReactNode;
  /** Возвращает компонент фильтра смен. */
  readonly shiftFilter: ReactNode;
}

/**
 * Представляет компонент адаптивного меню панели управления на странице "Наряд-задания".
 */
export function ResponsiveToolbar(props: ResponsiveToolbarProps) {
  const {
    hiddenCount,
    planedCount,
    clearButton,
    copyButton,
    submitButton,
    taskStatusFilter,
    vehiclesFilter,
    shiftFilter,
  } = props;

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
        {hiddenCount > ITEMS_PRIORITY.PLANNED_COUNT && planedCount}
        {hiddenCount > ITEMS_PRIORITY.TASK_STATUS_FILTER && taskStatusFilter}
        {hiddenCount > ITEMS_PRIORITY.VEHICLES_FILTER && vehiclesFilter}
        {hiddenCount > ITEMS_PRIORITY.SHIFT_FILTER && shiftFilter}
        {hiddenCount > ITEMS_PRIORITY.ACTION_BUTTONS && (
          <>
            <div className={styles.divider}>
              <div className={styles.divider_line} />
            </div>
            <div>{clearButton}</div>
            <div>{copyButton}</div>

            {hiddenCount > ITEMS_PRIORITY.SUBMIT_BUTTON && submitButton}
          </>
        )}
      </Popover.Dropdown>
    </Popover>
  );
}
