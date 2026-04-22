import type { Ref } from 'react';

import type { RouteTaskResponse } from '@/shared/api/endpoints/tasks';
import { cn } from '@/shared/lib/classnames-utils';
import { NO_DATA } from '@/shared/lib/constants';
import { hasValue } from '@/shared/lib/has-value';
import { useCargoMetrics } from '@/shared/lib/hooks/useCargoMetrics';

import { getCargoLabel, getPlaceLabelFromRouteData } from '../../lib/place-label';
import { useRouteTaskPlaceNames } from '../../lib/useRouteTaskPlaceNames';
import { getRouteStatusLabel, getRouteStatusVariant } from '../../model/status-map';

import styles from './RouteTaskRow.module.css';

/**
 * Пропсы строки таблицы маршрутов.
 */
interface RouteTaskRowProps {
  /** Порядковый номер строки (0-based, отображается как index+1). */
  readonly index: number;
  /** Данные маршрутного задания. */
  readonly task: RouteTaskResponse;
  /** Выделена ли строка в списке. */
  readonly isSelected: boolean;
  /** Колбэк выбора строки. */
  readonly onSelect: () => void;
  /** Ref на корневую кнопку (автопрокрутка списка). */
  readonly rowRef?: Ref<HTMLButtonElement | null>;
}

/**
 * Строка таблицы наряд-заданий (один route_task).
 */
export const RouteTaskRow = ({ index, task, isSelected, onSelect, rowRef }: RouteTaskRowProps) => {
  const { placeAName, placeBName } = useRouteTaskPlaceNames(task.place_a_id, task.place_b_id);
  const { cargoTypeName } = useCargoMetrics(task.place_b_id);
  const variant = getRouteStatusVariant(task.status);
  const start = getPlaceLabelFromRouteData(task.place_a_id, task.route_data, 'place_a_name', placeAName);
  const end = getPlaceLabelFromRouteData(task.place_b_id, task.route_data, 'place_b_name', placeBName);
  const cargo = getCargoLabel(task.type_task, task.route_data, cargoTypeName);
  const statusLabel = getRouteStatusLabel(task.status);

  return (
    <button
      ref={rowRef}
      type="button"
      className={cn(styles.row, isSelected && styles.row_selected)}
      onClick={onSelect}
    >
      <span>{index + 1}</span>
      <span>{start}</span>
      <span>{end}</span>
      <span>
        {task.actual_trips_count}/{task.planned_trips_count}
      </span>
      <span>{hasValue(task.weight) ? `${task.weight}` : NO_DATA.LONG_DASH}</span>
      <span>{hasValue(task.volume) ? `${task.volume}` : NO_DATA.LONG_DASH}</span>
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
        {statusLabel}
      </span>
    </button>
  );
};
