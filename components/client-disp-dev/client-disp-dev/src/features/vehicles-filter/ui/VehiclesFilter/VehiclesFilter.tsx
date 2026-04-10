import type { FloatingPosition, MenuProps } from '@mantine/core';
import { useMemo, useState } from 'react';

import type { Vehicle } from '@/shared/api/endpoints/vehicles';
import { cn } from '@/shared/lib/classnames-utils';
import { getMapGroupedByField } from '@/shared/lib/get-map-grouped-by-field';
import { Menu } from '@/shared/ui/Menu';
import { MenuTargetButton } from '@/shared/ui/MenuTargetButton';

import { VehiclesFilterList } from '../VehiclesFilterList';

import styles from './VehiclesFilter.module.css';

/** Представляет свойства компонента фильтра по транспортным средствам. */
interface VehiclesFilterProps extends Pick<MenuProps, 'position' | 'offset' | 'withinPortal'> {
  /** Возвращает список транспортных средств. */
  readonly vehicles: readonly Vehicle[];
  /** Возвращает список идентификаторов выбранных транспортных средств для фильтрации. */
  readonly selectedVehicleIds: Set<number>;
  /** Возвращает делегат, вызываемый при добавлении элементов фильтрации. */
  readonly onAddVehiclesFromFilter: (vehicleIds: readonly number[]) => void;
  /** Возвращает делегат, вызываемый при удалении элементов фильтрации. */
  readonly onRemoveVehiclesFromFilter: (vehicleIds: readonly number[]) => void;
  /** Возвращает позицию для отображения всплывающего окна. */
  readonly position?: FloatingPosition;
  /** Возвращает смещение всплывающего окна. */
  readonly offset?: number;
}

/**
 * Представляет компонент фильтра по транспортным средствам.
 */
export function VehiclesFilter(props: VehiclesFilterProps) {
  const {
    vehicles,
    selectedVehicleIds,
    onAddVehiclesFromFilter,
    onRemoveVehiclesFromFilter,
    position,
    offset,
    withinPortal,
  } = props;

  const groupedVehiclesByType = useMemo(() => getMapGroupedByField(vehicles, 'vehicle_type'), [vehicles]);

  const [opened, setOpened] = useState(false);

  const selectedVehiclesCount = selectedVehicleIds.size;

  return (
    <Menu
      onChange={setOpened}
      closeOnClickOutside
      width="target"
      position={position}
      offset={offset}
      withinPortal={withinPortal}
    >
      <Menu.Target>
        <div>
          <MenuTargetButton
            opened={opened}
            label="Выбрано объектов"
            afterLabel={
              <div className={cn(styles.count_container, { [styles.empty]: selectedVehiclesCount === 0 })}>
                {selectedVehiclesCount > 0 && <p>{selectedVehiclesCount}</p>}
              </div>
            }
          />
        </div>
      </Menu.Target>

      <Menu.Dropdown>
        {Array.from(groupedVehiclesByType).map(([vehicleType, groupVehicles]) => (
          <VehiclesFilterList
            key={vehicleType}
            vehicleType={vehicleType}
            vehicles={groupVehicles}
            selectedVehicleIds={selectedVehicleIds}
            onAddVehiclesFromFilter={onAddVehiclesFromFilter}
            onRemoveVehiclesFromFilter={onRemoveVehiclesFromFilter}
          />
        ))}
      </Menu.Dropdown>
    </Menu>
  );
}
