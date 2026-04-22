import {
  type CycleStateHistory,
  type StateHistory,
  useCreateUpdateStateHistoryMutation,
} from '@/shared/api/endpoints/state-history';
import type { Status } from '@/shared/api/endpoints/statuses';
import { assertHasValue } from '@/shared/lib/assert-has-value';
import { NO_DATA } from '@/shared/lib/constants';
import { calculateDuration, getTimeDurationDisplayValue } from '@/shared/lib/format-time-duration';
import { useTimezone } from '@/shared/lib/hooks/useTimezone';
import { AppButton } from '@/shared/ui/AppButton';
import { ContentString } from '@/shared/ui/ContentString';
import { Modal } from '@/shared/ui/Modal';
import { toast } from '@/shared/ui/Toast';

import styles from './SplitStatusModal.module.css';

/** Представляет свойства компонента модального окна для разделения статуса. */
interface SplitStatusModalProps {
  /** Возвращает состояние открытия. */
  readonly isOpen: boolean;
  /** Возвращает делегат вызываемый при закрытии. */
  readonly onClose: () => void;
  /** Возвращает делегат вызываемый при успешном разделении. */
  readonly onConfirm: () => void;
  /** Возвращает выбранный статус. */
  readonly status: CycleStateHistory;
  /** Возвращает следующий статус (за выбранным). */
  readonly nextStatus: StateHistory | null;
  /** Возвращает список статусов. */
  readonly statuses: readonly Status[];
}

/**
 * Представляет компонент модального окна для разделения статуса.
 */
export function SplitStatusModal(props: SplitStatusModalProps) {
  const { isOpen, onClose, onConfirm, status, nextStatus, statuses } = props;

  const tz = useTimezone();

  const now = new Date();

  const statusDuration = calculateDuration(status.timestamp, nextStatus?.timestamp ?? now);

  const halfStatusDuration = statusDuration / 2;

  const halfStatusDurationDisplayValue = getTimeDurationDisplayValue(halfStatusDuration);

  const middleTimestamp = new Date(new Date(status.timestamp).getTime() + halfStatusDuration);

  const statusConfiguration = statuses.find((item) => item.system_name === status.state);

  const statusName = statusConfiguration?.display_name ?? NO_DATA.DASH;
  const firstStatusStartTime = tz.format(status.timestamp, 'HH:mm:ss');
  const firstStatusStartDate = tz.format(status.timestamp, 'dd.MM.yyyy');
  const firstStatusEndTime = tz.format(middleTimestamp, 'HH:mm:ss');
  const firstStatusEndDate = tz.format(middleTimestamp, 'dd.MM.yyyy');

  const secondStatusStartTime = tz.format(middleTimestamp, 'HH:mm:ss');
  const secondStatusStartDate = tz.format(middleTimestamp, 'dd.MM.yyyy');
  const secondStatusEndTime = tz.format(nextStatus?.timestamp ?? now, 'HH:mm:ss');
  const secondStatusEndDate = tz.format(nextStatus?.timestamp ?? now, 'dd.MM.yyyy');

  const [createUpdateStateHistoryTrigger, { isLoading }] = useCreateUpdateStateHistoryMutation();

  const onConfirmSplit = async () => {
    assertHasValue(statusConfiguration);
    try {
      const response = createUpdateStateHistoryTrigger({
        vehicle_id: status.vehicle_id,
        items: [
          {
            id: null,
            timestamp: middleTimestamp.toISOString(),
            system_name: statusConfiguration.system_name,
            system_status: statusConfiguration.system_status,
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
      onConfirm();
    }
  };

  return (
    <Modal
      opened={isOpen}
      onClose={onClose}
      title={<p className={styles.title}>После разделения будет два статуса:</p>}
      centered
      size={530}
    >
      <div className={styles.body}>
        <div className={styles.content}>
          <div className={styles.content_block}>
            <p className={styles.block_title}>Статус 1</p>
            <ContentString
              title="Наименование"
              values={[statusName]}
            />
            <ContentString
              title="Начало"
              values={[firstStatusStartTime, firstStatusStartDate]}
            />
            <ContentString
              title="Конец"
              values={[firstStatusEndTime, firstStatusEndDate]}
            />
            <ContentString
              title="Продолжительность"
              values={[halfStatusDurationDisplayValue]}
            />
          </div>
          <div className={styles.content_block}>
            <p className={styles.block_title}>Статус 2</p>
            <ContentString
              title="Наименование"
              values={[statusName]}
            />
            <ContentString
              title="Начало"
              values={[secondStatusStartTime, secondStatusStartDate]}
            />
            <ContentString
              title="Конец"
              values={[secondStatusEndTime, secondStatusEndDate]}
            />
            <ContentString
              title="Продолжительность"
              values={[halfStatusDurationDisplayValue]}
            />
          </div>
        </div>
        <div className={styles.buttons}>
          <AppButton
            size="m"
            variant="secondary"
            onClick={onClose}
            fullWidth
            disabled={isLoading}
          >
            Отмена
          </AppButton>
          <AppButton
            size="m"
            onClick={onConfirmSplit}
            fullWidth
            loading={isLoading}
          >
            Разделить
          </AppButton>
        </div>
      </div>
    </Modal>
  );
}
