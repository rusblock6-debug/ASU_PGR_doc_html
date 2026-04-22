import { useMemo, useState } from 'react';

import { StatusList } from '@/features/status-list';

import { type AssignPlaceType } from '@/shared/api/endpoints/fleet-control';
import { useCreateUpdateStateHistoryMutation } from '@/shared/api/endpoints/state-history';
import { type Status, useGetAllStatusesQuery } from '@/shared/api/endpoints/statuses';
import ArrowDownIcon from '@/shared/assets/icons/ic-arrow-down.svg?react';
import ArrowRightWithTailIcon from '@/shared/assets/icons/ic-arrow-right-with-tail.svg?react';
import PlusIcon from '@/shared/assets/icons/ic-plus.svg?react';
import { cn } from '@/shared/lib/classnames-utils';
import { EMPTY_ARRAY, Z_INDEX } from '@/shared/lib/constants';
import { hasValue } from '@/shared/lib/has-value';
import { Popover } from '@/shared/ui/Popover';
import { toast } from '@/shared/ui/Toast';

import { useFleetControlPageDataSource } from '../../../lib/hooks/useFleetControlPageDataSource';

import { MoveIn } from './MoveIn';
import styles from './VehicleContextMenu.module.css';

/** Элементы меню. */
const MENU_ITEMS = {
  assignNewStatus: 'assignNewStatus',
  moveIn: 'moveIn',
} as const;

type MenuItemType = (typeof MENU_ITEMS)[keyof typeof MENU_ITEMS];

/**
 * Представляет свойства компонента всплывающего окна контекстного меню техники.
 */
interface VehicleContextMenuProps {
  /** Возвращает идентификатор оборудования. */
  readonly vehicleId: number;
  /** Возвращает наименование оборудования. */
  readonly name: string;
  /** Возвращает делегат, вызываемый при закрытии контекстного меню. */
  readonly onClose: () => void;
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
 * Представляет компонент всплывающего окна контекстного меню техники.
 */
export function VehicleContextMenu({
  vehicleId,
  name,
  onClose,
  currentAssignedPlace,
  currentGarageId,
  currentRoutePlaceAId,
  currentRoutePlaceBId,
}: VehicleContextMenuProps) {
  const { refetchFleetControlData } = useFleetControlPageDataSource();

  const { data: statusesData } = useGetAllStatusesQuery();

  const statuses = useMemo(() => statusesData?.items ?? EMPTY_ARRAY, [statusesData]);

  const [selectedItem, setSelectedItem] = useState<MenuItemType>();

  const handleSelect = (value: MenuItemType) => {
    setSelectedItem(value);
  };

  const handleClose = () => {
    setSelectedItem(undefined);
    onClose();
  };

  const [createUpdateStateHistoryTrigger] = useCreateUpdateStateHistoryMutation();

  const assignNewStatus = async (selectedStatus: Status) => {
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

      void refetchFleetControlData();
    } finally {
      handleClose();
    }
  };

  return (
    <div className={styles.root}>
      <Popover
        width={272}
        position="right"
        offset={10}
        zIndex={Z_INDEX.STICKY}
        withinPortal={false}
      >
        <Popover.Target>
          <div
            className={cn(styles.menu_item, { [styles.selected]: selectedItem === MENU_ITEMS.assignNewStatus })}
            onClick={() => handleSelect(MENU_ITEMS.assignNewStatus)}
          >
            <PlusIcon className={styles.item_icon} />
            <p>Назначить новый статус</p>
            <ArrowDownIcon className={styles.arrow_icon} />
          </div>
        </Popover.Target>
        <Popover.Dropdown className={styles.dropdown}>
          <div className={styles.title_container}>
            <PlusIcon />
            <p className={styles.title}>Назначить новый статус</p>
          </div>
          <StatusList
            statuses={statuses}
            searchable
            onSelect={assignNewStatus}
          />
        </Popover.Dropdown>
      </Popover>
      {hasValue(currentAssignedPlace) && (
        <Popover
          width={272}
          position="right"
          offset={10}
          zIndex={Z_INDEX.STICKY}
          withinPortal={false}
        >
          <Popover.Target>
            <div
              className={cn(styles.menu_item, { [styles.selected]: selectedItem === MENU_ITEMS.moveIn })}
              onClick={() => handleSelect(MENU_ITEMS.moveIn)}
            >
              <ArrowRightWithTailIcon className={styles.item_icon} />
              <p>Переместить в</p>
              <ArrowDownIcon className={styles.arrow_icon} />
            </div>
          </Popover.Target>
          <Popover.Dropdown className={styles.dropdown}>
            <MoveIn
              vehicleId={vehicleId}
              vehicleName={name}
              currentAssignedPlace={currentAssignedPlace}
              currentGarageId={currentGarageId}
              currentRoutePlaceAId={currentRoutePlaceAId}
              currentRoutePlaceBId={currentRoutePlaceBId}
              onClose={onClose}
            />
          </Popover.Dropdown>
        </Popover>
      )}
    </div>
  );
}
