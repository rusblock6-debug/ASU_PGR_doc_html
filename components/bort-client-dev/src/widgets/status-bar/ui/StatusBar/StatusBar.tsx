import { getRouteStatusLabel, resolveVehicleStateUiLabel } from '@/entities/route-task';

import type { StatusResponse } from '@/shared/api/endpoints/statuses';
import type { RouteTaskResponse } from '@/shared/api/endpoints/tasks';
import type { VehicleState } from '@/shared/api/types/vehicle-events';
import ChevronRightIcon from '@/shared/assets/icons/ic-chevron-right.svg?react';

import styles from './StatusBar.module.css';

/** Пропсы нижней плашки статуса рейса и состояния борта. */
interface StatusBarProps {
  /** Активное маршрутное задание; `null` — нет активного. */
  readonly task: RouteTaskResponse | null;
  /** Текущее состояние борта из SSE-потока. */
  readonly streamStateStatus?: VehicleState | null;
  /** Справочник простоев (enterprise) — подпись для `system_name`, не совпадающих со стандартной цепочкой. */
  readonly downtimeStatuses?: readonly StatusResponse[] | null;
  /** Время в текущем состоянии (отформатированная строка). */
  readonly elapsed?: string | null;
  /** Открыть экран управления статусом (кнопка вместо секции). */
  readonly onOpenVehicleStatus?: () => void;
}

/**
 * Нижняя плашка со статусом и таймером текущего состояния борта.
 */
export const StatusBar = ({
  task,
  streamStateStatus,
  downtimeStatuses,
  elapsed,
  onOpenVehicleStatus,
}: StatusBarProps) => {
  let statusLabel = 'НЕТ СТАТУСА';
  if (streamStateStatus) {
    statusLabel = resolveVehicleStateUiLabel(streamStateStatus, downtimeStatuses ?? undefined);
  } else if (task) {
    statusLabel = getRouteStatusLabel(task.status);
  }

  const words = statusLabel.split(' ');
  const firstWord = words[0];
  const restWords = words.slice(1).join(' ');
  const subLine = [restWords, elapsed].filter(Boolean).join(' ');

  const textContent = (
    <>
      <span className={styles.status}>{firstWord}</span>
      {subLine ? <span className={styles.status_sub}>{subLine}</span> : null}
    </>
  );

  if (onOpenVehicleStatus) {
    return (
      <button
        type="button"
        className={styles.root}
        aria-label="Открыть управление статусом"
        onClick={onOpenVehicleStatus}
      >
        <div className={styles.text_content}>{textContent}</div>
        <ChevronRightIcon
          className={styles.arrow}
          aria-hidden
        />
      </button>
    );
  }

  return <section className={styles.root}>{textContent}</section>;
};
