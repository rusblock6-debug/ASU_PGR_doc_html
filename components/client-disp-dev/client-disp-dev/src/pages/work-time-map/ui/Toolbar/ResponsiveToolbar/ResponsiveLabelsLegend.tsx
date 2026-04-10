import { useState } from 'react';

import { StatusList } from '@/features/StatusList';

import type { Status } from '@/shared/api/endpoints/statuses';
import { Menu } from '@/shared/ui/Menu';
import { MenuTargetButton } from '@/shared/ui/MenuTargetButton';

/**
 * Представляет свойства компонента легенды обозначений для адаптивной панели управления на странице "Карта рабочего времени".
 */
interface ResponsiveLabelsLegendProps {
  /** Возвращает список статусов. */
  readonly statuses: readonly Status[];
}

/**
 * Представляет компонент легенды обозначений для адаптивной панели управления на странице "Карта рабочего времени".
 */
export function ResponsiveLabelsLegend(props: ResponsiveLabelsLegendProps) {
  const { statuses } = props;

  const [opened, setOpened] = useState(false);

  return (
    <Menu
      onChange={setOpened}
      closeOnClickOutside
      width="target"
    >
      <Menu.Target>
        <div>
          <MenuTargetButton
            opened={opened}
            label="Легенда обозначений"
          />
        </div>
      </Menu.Target>

      <Menu.Dropdown>
        <StatusList statuses={statuses} />
      </Menu.Dropdown>
    </Menu>
  );
}
