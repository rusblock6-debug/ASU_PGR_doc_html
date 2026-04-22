import { type ComponentProps, useState } from 'react';

import { VehicleMarker } from '@/entities/vehicle';

import type { AssignPlaceType } from '@/shared/api/endpoints/fleet-control';
import { hasValue } from '@/shared/lib/has-value';
import { Popover } from '@/shared/ui/Popover';
import { Tooltip } from '@/shared/ui/Tooltip';

import styles from './FleetControlVehicleMarker.module.css';
import { VehicleContextMenu } from './VehicleContextMenu';
import { VehiclePopup } from './VehiclePopup';

/**
 * Представляет свойства компонента маркера оборудования на странице "Управление техникой".
 */
export interface FleetControlVehicleMarkerProps extends ComponentProps<typeof VehicleMarker> {
  /** Возвращает идентификатор оборудования. */
  readonly vehicleId: number;
  /** Возвращает тип текущего назначенного места. */
  readonly currentAssignedPlace?: AssignPlaceType;
  /** Возвращает идентификатор текущего гаража. */
  readonly currentGarageId?: number;
  /** Возвращает идентификатор текущего места погрузки. */
  readonly currentRoutePlaceAId?: number;
  /** Возвращает идентификатор текущего места разгрузки. */
  readonly currentRoutePlaceBId?: number;
}

/**
 * Представляет компонент маркера оборудования на странице "Управление техникой".
 */
export function FleetControlVehicleMarker({
  vehicleId,
  currentAssignedPlace,
  currentGarageId,
  currentRoutePlaceAId,
  currentRoutePlaceBId,
  ...vehicleMarkerProps
}: FleetControlVehicleMarkerProps) {
  const [dropdownMode, setDropdownMode] = useState<'popup' | 'context' | null>(null);

  const isOpenDropdown = hasValue(dropdownMode);

  const onClose = () => {
    setDropdownMode(null);
  };

  return (
    <Popover
      opened={isOpenDropdown}
      position={dropdownMode === 'popup' ? 'top' : 'right'}
      onDismiss={onClose}
      closeOnClickOutside
      closeOnEscape
    >
      <Popover.Target>
        <Tooltip
          label="Оператор техники пока не принял новое наряд-задание"
          disabled={!hasValue(vehicleMarkerProps.iconOpacity)}
        >
          <VehicleMarker
            {...vehicleMarkerProps}
            size="s"
            isNormalLabelPosition
            selected={isOpenDropdown}
            onClick={() => {
              setDropdownMode('popup');
            }}
            onContextMenu={() => {
              setDropdownMode('context');
            }}
          />
        </Tooltip>
      </Popover.Target>

      {isOpenDropdown && (
        <Popover.Dropdown className={styles.dropdown}>
          {dropdownMode === 'popup' && (
            <VehiclePopup
              vehicleId={vehicleId}
              name={vehicleMarkerProps.name}
              onClose={onClose}
            />
          )}
          {dropdownMode === 'context' && (
            <VehicleContextMenu
              vehicleId={vehicleId}
              name={vehicleMarkerProps.name}
              onClose={onClose}
              currentAssignedPlace={currentAssignedPlace}
              currentGarageId={currentGarageId}
              currentRoutePlaceAId={currentRoutePlaceAId}
              currentRoutePlaceBId={currentRoutePlaceBId}
            />
          )}
        </Popover.Dropdown>
      )}
    </Popover>
  );
}
