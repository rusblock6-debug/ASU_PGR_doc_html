import type { RouteTaskResponse } from '@/shared/api/types/trip-service';
import { cn } from '@/shared/lib/classnames-utils';
import { NO_DATA } from '@/shared/lib/constants';
import { useCargoMetrics } from '@/shared/lib/hooks/useCargoMetrics';

import { getCargoLabel, getPlaceLabelFromRouteData } from '../../lib/place-label';
import { useRouteTaskPlaceNames } from '../../lib/use-route-task-place-names';
import { getRouteStatusLabel, getRouteStatusVariant, isRouteTaskInProgress } from '../../model/status-map';

import styles from './RouteTaskRow.module.css';

/**
 * Пропсы строки таблицы маршрутов.
 */
interface RouteTaskRowProps {
  readonly index: number;
  readonly task: RouteTaskResponse;
  readonly isSelected: boolean;
  readonly onSelect: () => void;
}

/**
 * Строка таблицы наряд-заданий (один route_task).
 */
export const RouteTaskRow = ({ index, task, isSelected, onSelect }: RouteTaskRowProps) => {
  const { placeAName, placeBName } = useRouteTaskPlaceNames(task.place_a_id, task.place_b_id);
  const { cargoTypeName } = useCargoMetrics(task.place_b_id);
  const variant = getRouteStatusVariant(task.status);
  const inProgress = isRouteTaskInProgress(task.status);
  const start = getPlaceLabelFromRouteData(task.place_a_id, task.route_data, 'place_a_name', placeAName);
  const end = getPlaceLabelFromRouteData(task.place_b_id, task.route_data, 'place_b_name', placeBName);
  const cargo = getCargoLabel(task.type_task, task.route_data, cargoTypeName);
  const statusLabel = getRouteStatusLabel(task.status);

  return (
    <button
      type="button"
      className={cn(styles.row, isSelected && styles.row_selected, inProgress && styles.row_active)}
      onClick={onSelect}
    >
      <span>{index + 1}</span>
      <span>{start}</span>
      <span>{end}</span>
      <span>
        {task.actual_trips_count}/{task.planned_trips_count}
      </span>
      <span>{task.weight != null ? `${task.weight}` : NO_DATA.LONG_DASH}</span>
      <span>{task.volume != null ? `${task.volume}` : NO_DATA.LONG_DASH}</span>
      <span className={styles.cell_muted}>{cargo}</span>
      <span
        className={cn(
          variant === 'waiting' && styles.status_waiting,
          variant === 'active' && styles.status_active,
          variant === 'paused' && styles.status_paused,
          variant === 'cancelled' && styles.status_cancelled,
          variant === 'done' && styles.status_done,
        )}
      >
        {inProgress ? <span className={styles.action_pill}>ДЕЙСТВИЕ</span> : statusLabel}
      </span>
    </button>
  );
};
