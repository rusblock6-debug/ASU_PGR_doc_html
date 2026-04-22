import { type ReactNode, useState } from 'react';

import { Popover } from '@/shared/ui/Popover';
import { ResponsiveMenuButton } from '@/shared/ui/ResponsiveMenuButton';

import { Divider } from '../../Divider';

import styles from './ResponsiveToolbar.module.css';

/** Приоритеты отображения для элементов панели управления. */
export const ITEMS_PRIORITY = {
  ROUTE_FILTER: 0,
  MODE_SWITCHER: 1,
  ADD_ROUTE: 2,
} as const;

/**
 * Представляет свойства компонента адаптивного меню панели управления на странице "Управление техникой".
 */
interface ResponsiveToolbarProps {
  /** Возвращает количество скрытых элементов. */
  readonly hiddenCount: number;
  /** Возвращает компонент фильтра маршрутов. */
  readonly routesFilter: ReactNode;
  /** Возвращает компонент переключателю режимов отображения маршрутов. */
  readonly modeSwitcher: ReactNode;
  /** Возвращает компонент кнопки добавления маршрута. */
  readonly addRouteButton: ReactNode;
}

/**
 * Представляет компонент адаптивного меню панели управления на странице "Управление техникой".
 */
export function ResponsiveToolbar(props: ResponsiveToolbarProps) {
  const { hiddenCount, routesFilter, modeSwitcher, addRouteButton } = props;

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
        {hiddenCount > ITEMS_PRIORITY.ADD_ROUTE && addRouteButton}
        {hiddenCount > ITEMS_PRIORITY.ROUTE_FILTER && routesFilter}
        {hiddenCount > ITEMS_PRIORITY.MODE_SWITCHER && (
          <>
            <div className={styles.divider_container}>
              <Divider
                color="var(--line-fa-connector)"
                height={1}
              />
            </div>
            {modeSwitcher}
          </>
        )}
      </Popover.Dropdown>
    </Popover>
  );
}
