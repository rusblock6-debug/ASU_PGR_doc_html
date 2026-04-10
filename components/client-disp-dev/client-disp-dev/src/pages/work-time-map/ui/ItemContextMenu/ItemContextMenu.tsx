import { useState } from 'react';

import { StatusList } from '@/features/StatusList';

import {
  isCycleStateHistory,
  type StateHistory,
  useCreateUpdateStateHistoryMutation,
  useDeleteStateHistoryMutation,
} from '@/shared/api/endpoints/state-history';
import type { Status } from '@/shared/api/endpoints/statuses';
import ArrowDownIcon from '@/shared/assets/icons/ic-arrow-down.svg?react';
import CutIcon from '@/shared/assets/icons/ic-cut.svg?react';
import PencilIcon from '@/shared/assets/icons/ic-pencil.svg?react';
import PlusIcon from '@/shared/assets/icons/ic-plus.svg?react';
import TrashIcon from '@/shared/assets/icons/ic-trash.svg?react';
import { cn } from '@/shared/lib/classnames-utils';
import { Z_INDEX } from '@/shared/lib/constants';
import { hasValue } from '@/shared/lib/has-value';
import { useElementPositioning } from '@/shared/lib/hooks/useElementPositioning';
import { useClickOutside } from '@/shared/lib/hooks/useOutsideClick';
import { useOutsideScroll } from '@/shared/lib/hooks/useOutsideScroll';
import { ConfirmModal } from '@/shared/ui/ConfirmModal';
import { Popover } from '@/shared/ui/Popover';
import { toast } from '@/shared/ui/Toast';
import type { ElementCoordinates } from '@/shared/ui/types';

import { useWorkTimeMapPageContext } from '../../model/WorkTimeMapPageContext';
import { AddTripDrawer } from '../AddTripDrawer';
import { SplitStatusModal } from '../SplitStatusModal';

import styles from './ItemContextMenu.module.css';

/** Представляет свойства компонента контекстного меню элемента таймлайна. */
interface ItemContextMenuProps {
  /** Возвращает выбранный статус. */
  readonly status: StateHistory;
  /** Возвращает следующий статус (за выбранным). */
  readonly nextStatus: StateHistory | null;
  /** Возвращает координаты положения контекстного меню. */
  readonly coordinates: ElementCoordinates;
  /** Возвращает делегат, вызываемый при закрытии контекстного меню. */
  readonly onClose: () => void;
}

/** Элементы меню. */
const MENU_ITEMS = {
  addTrip: 'addTrip',
  add: 'add',
  edit: 'edit',
  split: 'split',
  remove: 'remove',
} as const;

type MenuItemType = (typeof MENU_ITEMS)[keyof typeof MENU_ITEMS];

/**
 * Представляет компонент контекстного меню элемента таймлайна.
 */
export function ItemContextMenu(props: ItemContextMenuProps) {
  const { status, nextStatus, coordinates, onClose } = props;
  const { statuses } = useWorkTimeMapPageContext();

  const isCycleStatus = isCycleStateHistory(status);

  const [selectedItem, setSelectedItem] = useState<MenuItemType>();

  const ref = useElementPositioning(coordinates);

  const isActiveClickOutside =
    selectedItem !== MENU_ITEMS.remove && selectedItem !== MENU_ITEMS.split && selectedItem !== MENU_ITEMS.addTrip;

  const canAddTrip = isCycleStatus && !hasValue(status.cycle_id);

  useClickOutside(ref, onClose, isActiveClickOutside);
  useOutsideScroll(ref, onClose);

  const handleSelect = (value: MenuItemType) => {
    setSelectedItem(value);
  };

  const handleClose = () => {
    setSelectedItem(undefined);
    onClose();
  };

  const [deleteStateHistoryTrigger, { data: deleteStateHistoryData, isLoading: isLoadingDeleteStateHistoryData }] =
    useDeleteStateHistoryMutation();

  const onDeleteStateHistory = async () => {
    const response = await deleteStateHistoryTrigger({ id: status.id, confirm: false });
    if (response.data?.message) {
      handleSelect(MENU_ITEMS.remove);
    }
  };

  const onConfirmDeleteStateHistory = async () => {
    try {
      const response = deleteStateHistoryTrigger({ id: status.id, confirm: true }).unwrap();

      await toast.promise(response, {
        loading: { message: 'Сохранение изменений' },
        success: { message: 'Изменения сохранены' },
        error: { message: 'Ошибка сохранения' },
      });
    } finally {
      handleClose();
    }
  };

  const [createUpdateStateHistoryTrigger] = useCreateUpdateStateHistoryMutation();

  const assignNewStatus = async (selectedStatus: Status) => {
    try {
      const response = createUpdateStateHistoryTrigger({
        vehicle_id: status.vehicle_id,
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

  const updateStatus = async (selectedStatus: Status) => {
    if (isCycleStatus) {
      try {
        const response = createUpdateStateHistoryTrigger({
          vehicle_id: status.vehicle_id,
          items: [
            {
              id: status.id,
              timestamp: status.timestamp,
              system_name: selectedStatus.system_name,
              system_status: selectedStatus.system_status,
              cycle_id: status.cycle_id,
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
    }
  };

  return (
    <div
      ref={ref}
      className={styles.root}
    >
      {canAddTrip && (
        <div
          className={cn(styles.menu_item, { [styles.selected]: selectedItem === MENU_ITEMS.addTrip })}
          onClick={() => handleSelect(MENU_ITEMS.addTrip)}
        >
          <PlusIcon className={styles.item_icon} />
          <p>Добавить рейс</p>
        </div>
      )}

      <Popover
        width={272}
        position="right"
        offset={10}
        zIndex={Z_INDEX.STICKY}
        classNames={{
          dropdown: styles.dropdown,
        }}
        withinPortal={false}
      >
        <Popover.Target>
          <div
            className={cn(styles.menu_item, { [styles.selected]: selectedItem === MENU_ITEMS.add })}
            onClick={() => handleSelect(MENU_ITEMS.add)}
          >
            <PlusIcon className={styles.item_icon} />
            <p>Назначить новый статус</p>
            <ArrowDownIcon className={styles.arrow_icon} />
          </div>
        </Popover.Target>
        <Popover.Dropdown>
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

      {isCycleStatus && (
        <Popover
          width={272}
          position="right"
          offset={10}
          zIndex={Z_INDEX.STICKY}
          classNames={{
            dropdown: styles.dropdown,
          }}
          withinPortal={false}
        >
          <Popover.Target>
            <div
              className={cn(styles.menu_item, { [styles.selected]: selectedItem === MENU_ITEMS.edit })}
              onClick={() => handleSelect(MENU_ITEMS.edit)}
            >
              <PencilIcon className={styles.item_icon} />
              <p>Изменить статус</p>
              <ArrowDownIcon className={styles.arrow_icon} />
            </div>
          </Popover.Target>
          <Popover.Dropdown>
            <div className={styles.title_container}>
              <PencilIcon />
              <p className={styles.title}>Изменить статус</p>
            </div>
            <StatusList
              statuses={statuses}
              searchable
              onSelect={updateStatus}
            />
          </Popover.Dropdown>
        </Popover>
      )}

      {isCycleStatus && (
        <div
          className={cn(styles.menu_item, { [styles.selected]: selectedItem === MENU_ITEMS.split })}
          onClick={() => handleSelect(MENU_ITEMS.split)}
        >
          <CutIcon className={styles.item_icon} />
          <p>Разделить статус</p>
        </div>
      )}

      {isCycleStatus && (
        <div
          className={cn(styles.menu_item, { [styles.selected]: selectedItem === MENU_ITEMS.remove })}
          onClick={onDeleteStateHistory}
        >
          <TrashIcon className={styles.item_icon} />
          <p>Удалить</p>
        </div>
      )}

      {isCycleStatus && (
        <SplitStatusModal
          isOpen={selectedItem === MENU_ITEMS.split}
          onClose={handleClose}
          onConfirm={handleClose}
          status={status}
          nextStatus={nextStatus}
          statuses={statuses}
        />
      )}

      <ConfirmModal
        isOpen={selectedItem === MENU_ITEMS.remove}
        onClose={handleClose}
        onConfirm={onConfirmDeleteStateHistory}
        title={deleteStateHistoryData?.message || 'Удаление...'}
        confirmButtonText="Удалить"
        isLoading={isLoadingDeleteStateHistoryData}
      />

      {isCycleStatus && (
        <AddTripDrawer
          isOpen={selectedItem === MENU_ITEMS.addTrip}
          onClose={handleClose}
          status={status}
          nextStatus={nextStatus}
        />
      )}
    </div>
  );
}
