import { StatusList } from '@/features/StatusList';

import { useCreateUpdateStateHistoryMutation } from '@/shared/api/endpoints/state-history';
import type { Status } from '@/shared/api/endpoints/statuses';
import PlusIcon from '@/shared/assets/icons/ic-plus.svg?react';
import { useElementPositioning } from '@/shared/lib/hooks/useElementPositioning';
import { useClickOutside } from '@/shared/lib/hooks/useOutsideClick';
import { useOutsideScroll } from '@/shared/lib/hooks/useOutsideScroll';
import { toast } from '@/shared/ui/Toast';
import type { ElementCoordinates } from '@/shared/ui/types';

import { useWorkTimeMapPageContext } from '../../model/WorkTimeMapPageContext';

import styles from './GroupContextMenu.module.css';

/** Представляет свойства компонента контекстного меню группы таймлайна. */
interface GroupContextMenuProps {
  /** Возвращает идентификатор группы. */
  readonly groupId: number;
  /** Возвращает координаты положения контекстного меню. */
  readonly coordinates: ElementCoordinates;
  /** Возвращает делегат, вызываемый при закрытии контекстного меню. */
  readonly onClose: () => void;
}

/**
 * Представляет компонент контекстного меню группы таймлайна.
 */
export function GroupContextMenu(props: GroupContextMenuProps) {
  const { groupId, coordinates, onClose } = props;
  const { statuses } = useWorkTimeMapPageContext();

  const ref = useElementPositioning(coordinates);

  useClickOutside(ref, onClose);
  useOutsideScroll(ref, onClose);

  const [createUpdateStateHistoryTrigger] = useCreateUpdateStateHistoryMutation();

  const onSelect = async (status: Status) => {
    try {
      const response = createUpdateStateHistoryTrigger({
        vehicle_id: groupId,
        items: [
          {
            id: null,
            timestamp: null,
            system_name: status.system_name,
            system_status: status.system_status,
          },
        ],
      }).unwrap();

      await toast.promise(response, {
        loading: { message: 'Сохранение изменений' },
        success: { message: 'Изменения сохранены' },
        error: { message: 'Ошибка сохранения' },
      });
    } finally {
      onClose();
    }
  };

  return (
    <div
      ref={ref}
      className={styles.root}
    >
      <div className={styles.title_container}>
        <PlusIcon />
        <p className={styles.title}>Назначить новый статус</p>
      </div>
      <StatusList
        statuses={statuses}
        searchable
        onSelect={onSelect}
      />
    </div>
  );
}
