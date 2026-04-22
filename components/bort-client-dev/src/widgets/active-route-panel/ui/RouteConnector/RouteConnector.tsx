import type { VehicleState } from '@/shared/api/types/vehicle-events';
import ArrowUpIcon from '@/shared/assets/icons/ic-arrow-up.svg?react';
import MapPinIcon from '@/shared/assets/icons/ic-map-pin.svg?react';
import { cn } from '@/shared/lib/classnames-utils';

import styles from './RouteConnector.module.css';

const EMPTY_STATES = new Set<VehicleState>(['unloading', 'moving_empty', 'stopped_empty']);

/** Пропсы вертикального коннектора между узлами активного маршрута. */
interface RouteConnectorProps {
  /** Процент прогресса маршрута (0–100, null — нет данных). */
  readonly progressPercent?: number | null;
  /** Состояние борта — определяет направление стрелки. */
  readonly vehicleState?: VehicleState | null;
}

/** Визуализирует прогресс маршрута и направление движения в активном рейсе. */
export const RouteConnector = ({ progressPercent, vehicleState }: RouteConnectorProps) => {
  const clampedPercent = progressPercent != null ? Math.min(100, Math.max(0, progressPercent)) : null;

  return (
    <div
      className={styles.root}
      aria-hidden
    >
      <MapPinIcon className={styles.pin} />
      <div className={styles.line}>
        {clampedPercent != null && (
          <div
            className={styles.fill}
            style={{ height: `${clampedPercent}%` }}
          />
        )}
      </div>
      {clampedPercent != null && (
        <div
          className={styles.circle}
          style={{ bottom: `${clampedPercent}%` }}
        >
          <ArrowUpIcon
            className={cn(
              styles.circle_icon,
              vehicleState && EMPTY_STATES.has(vehicleState) && styles.circle_icon_down,
            )}
          />
        </div>
      )}
    </div>
  );
};
