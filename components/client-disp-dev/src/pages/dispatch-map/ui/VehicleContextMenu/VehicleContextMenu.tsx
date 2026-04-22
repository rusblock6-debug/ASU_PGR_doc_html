import { UnstyledButton } from '@mantine/core';
import { useState } from 'react';
import { createPortal } from 'react-dom';

import { StatusList } from '@/features/status-list';

import { useMoveVehicleMutation } from '@/shared/api/endpoints/locations';
import type { Place } from '@/shared/api/endpoints/places';
import { useCreateUpdateStateHistoryMutation } from '@/shared/api/endpoints/state-history';
import { type Status, useGetAllStatusesQuery } from '@/shared/api/endpoints/statuses';
import ArrowDownIcon from '@/shared/assets/icons/ic-arrow-down.svg?react';
import PlaceIcon from '@/shared/assets/icons/ic-move.svg?react';
import PlusIcon from '@/shared/assets/icons/ic-plus.svg?react';
import { cn } from '@/shared/lib/classnames-utils';
import { EMPTY_ARRAY, Z_INDEX } from '@/shared/lib/constants';
import { useAppDispatch } from '@/shared/lib/hooks/useAppDispatch';
import { useAppSelector } from '@/shared/lib/hooks/useAppSelector';
import { useElementPositioning } from '@/shared/lib/hooks/useElementPositioning';
import { useClickOutside } from '@/shared/lib/hooks/useOutsideClick';
import { Popover } from '@/shared/ui/Popover';
import { toast } from '@/shared/ui/Toast';

import { useMapPlaces } from '../../lib/hooks/useMapPlaces';
import { selectVehicleContextMenu } from '../../model/selectors';
import { mapActions } from '../../model/slice';
import type { VehicleContextMenuState } from '../../model/types';

import { PlaceList } from './PlaceList';
import styles from './VehicleContextMenu.module.css';

const MENU_ITEMS = {
  AssignStatus: 'assignStatus',
  AssignLocation: 'setLocation',
} as const;

type MenuItemType = (typeof MENU_ITEMS)[keyof typeof MENU_ITEMS];

/**
 * Контекстное меню транспорта на карте.
 * Отображается через портал в `document.body`, т.к. вызывается из R3F Canvas, где нет `MantineProvider`.
 */
export function VehicleContextMenu() {
  const menuState = useAppSelector(selectVehicleContextMenu);
  if (!menuState) return null;

  return createPortal(<VehicleContextMenuContent {...menuState} />, document.body);
}

/**
 * Содержимое контекстного меню транспорта (позиционирование, пункты и действия).
 */
function VehicleContextMenuContent({ clickPosition, vehicleId }: Readonly<VehicleContextMenuState>) {
  const dispatch = useAppDispatch();
  const { data: statusesData } = useGetAllStatusesQuery();
  const { all: places, horizons } = useMapPlaces();

  const [selectedItem, setSelectedItem] = useState<MenuItemType>();

  const ref = useElementPositioning(clickPosition);

  const handleClose = () => {
    setSelectedItem(undefined);
    dispatch(mapActions.setVehicleContextMenu(null));
  };

  useClickOutside(ref, handleClose);

  const [createUpdateStateHistoryTrigger] = useCreateUpdateStateHistoryMutation();
  const [moveVehicleMutationTrigger] = useMoveVehicleMutation();

  const handleSelectStatus = async (selectedStatus: Status) => {
    try {
      const response = createUpdateStateHistoryTrigger({
        vehicle_id: vehicleId,
        items: [
          {
            id: null,
            timestamp: null,
            system_name: selectedStatus.system_name,
            system_status: selectedStatus.system_status,
          },
        ],
      }).unwrap();

      await toast.promise(response, {
        loading: { message: 'Сохранение изменений' },
        success: { message: 'Изменения сохранены' },
        error: { message: 'Ошибка сохранения' },
      });
    } finally {
      handleClose();
    }
  };

  const handleSelectPlace = async (place: Place) => {
    try {
      const response = moveVehicleMutationTrigger({
        vehicle_id: vehicleId,
        place_id: place.id,
      }).unwrap();

      await toast.promise(response, {
        loading: { message: 'Сохранение изменений' },
        success: { message: 'Изменения сохранены' },
        error: { message: 'Ошибка сохранения' },
      });
    } finally {
      handleClose();
    }
  };

  return (
    <div
      ref={ref}
      className={styles.root}
    >
      <div className={styles.menu}>
        <Popover
          width={272}
          position="right-start"
          offset={12}
          zIndex={Z_INDEX.STICKY}
          withinPortal={false}
        >
          <Popover.Target>
            <UnstyledButton
              type="button"
              className={cn(styles.menu_item, { [styles.selected]: selectedItem === MENU_ITEMS.AssignStatus })}
              onClick={() => setSelectedItem(MENU_ITEMS.AssignStatus)}
            >
              <PlusIcon className={styles.item_icon} />
              <p>Назначить новый статус</p>
              <ArrowDownIcon className={styles.arrow_icon} />
            </UnstyledButton>
          </Popover.Target>

          <Popover.Dropdown className={styles.dropdown}>
            <StatusList
              statuses={statusesData?.items ?? EMPTY_ARRAY}
              searchable
              onSelect={handleSelectStatus}
            />
          </Popover.Dropdown>
        </Popover>

        <Popover
          width={272}
          position="right-start"
          offset={12}
          zIndex={Z_INDEX.STICKY}
          withinPortal={false}
        >
          <Popover.Target>
            <UnstyledButton
              type="button"
              className={cn(styles.menu_item, { [styles.selected]: selectedItem === MENU_ITEMS.AssignLocation })}
              onClick={() => setSelectedItem(MENU_ITEMS.AssignLocation)}
            >
              <PlaceIcon className={styles.item_icon} />
              <p>Установить местоположение</p>
              <ArrowDownIcon className={styles.arrow_icon} />
            </UnstyledButton>
          </Popover.Target>

          <Popover.Dropdown className={styles.dropdown}>
            <PlaceList
              places={places}
              horizons={horizons}
              onSelect={handleSelectPlace}
            />
          </Popover.Dropdown>
        </Popover>
      </div>
    </div>
  );
}
