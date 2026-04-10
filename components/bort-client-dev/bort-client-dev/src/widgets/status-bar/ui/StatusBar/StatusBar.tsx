import { getRouteStatusLabel, getStateEventLabel } from '@/entities/route-task';

import type { RouteTaskResponse } from '@/shared/api/types/trip-service';
import type { VehicleState } from '@/shared/api/types/vehicle-events';

import styles from './StatusBar.module.css';

/** Пропсы нижней плашки статуса рейса и состояния борта. */
interface StatusBarProps {
  readonly task: RouteTaskResponse | null;
  readonly streamStateStatus?: VehicleState | null;
  readonly elapsed?: string | null;
  /** Открыть экран управления статусом (кнопка вместо секции). */
  readonly onOpenVehicleStatus?: () => void;
}

/**
 * Нижняя плашка со статусом и таймером текущего состояния борта.
 */
export const StatusBar = ({ task, streamStateStatus, elapsed, onOpenVehicleStatus }: StatusBarProps) => {
  let statusLabel = 'НЕТ СТАТУСА';
  if (streamStateStatus) {
    statusLabel = getStateEventLabel(streamStateStatus);
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
        <svg
          viewBox="0 0 24 24"
          className={styles.arrow}
          aria-hidden
        >
          <path d="M9 6l6 6-6 6" />
        </svg>
      </button>
    );
  }

  return <section className={styles.root}>{textContent}</section>;
};
