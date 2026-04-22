import type { RouteTaskResponse } from '@/shared/api/endpoints/tasks';
import { NO_DATA } from '@/shared/lib/constants';
import { hasValue } from '@/shared/lib/has-value';
import { useCargoMetrics } from '@/shared/lib/hooks/useCargoMetrics';

import { getCargoLabel, getPlaceLabelFromRouteData } from '../../lib/place-label';
import { useRouteTaskPlaceNames } from '../../lib/useRouteTaskPlaceNames';

import styles from './RouteTaskDetail.module.css';

/**
 * Пропсы карточки деталей маршрутного задания.
 */
interface RouteTaskDetailProps {
  /** Данные маршрутного задания (места, рейсы, вес/объём). */
  readonly task: RouteTaskResponse;
  /** Отформатированная строка расстояния; по умолчанию `—`. */
  readonly distanceLabel?: string;
  /** Отформатированная строка времени в пути; по умолчанию `—`. */
  readonly durationLabel?: string;
}

/**
 * Карточка деталей маршрута с ключевыми метриками и данными груза.
 */
export const RouteTaskDetail = ({
  task,
  distanceLabel = NO_DATA.LONG_DASH,
  durationLabel = NO_DATA.LONG_DASH,
}: RouteTaskDetailProps) => {
  const { placeAName, placeBName } = useRouteTaskPlaceNames(task.place_a_id, task.place_b_id);
  const { cargoTypeName } = useCargoMetrics(task.place_b_id);
  const start = getPlaceLabelFromRouteData(task.place_a_id, task.route_data, 'place_a_name', placeAName);
  const end = getPlaceLabelFromRouteData(task.place_b_id, task.route_data, 'place_b_name', placeBName);
  const cargo = getCargoLabel(task.type_task, task.route_data, cargoTypeName);

  return (
    <div className={styles.root}>
      <div className={styles.place_block}>
        <span className={styles.label}>НАЧАЛО МАРШРУТА</span>
        <span className={styles.place_value}>{start}</span>
      </div>

      <div className={styles.place_block}>
        <span className={styles.label}>КОНЕЦ МАРШРУТА</span>
        <span className={styles.place_value}>{end}</span>
      </div>

      <div className={styles.metrics_row}>
        <div className={styles.metric}>
          <span className={styles.label}>РАССТОЯНИЕ</span>
          <span className={styles.metric_value}>{distanceLabel}</span>
        </div>
        <div className={styles.metric}>
          <span className={styles.label}>ВРЕМЯ В ПУТИ</span>
          <span className={styles.metric_value_accent}>{durationLabel}</span>
        </div>
        <div className={styles.metric}>
          <span className={styles.label}>РЕЙСЫ</span>
          <span className={styles.metric_value}>
            {task.actual_trips_count}/{task.planned_trips_count}
          </span>
        </div>
      </div>

      <div className={styles.metrics_row}>
        <div className={styles.metric}>
          <span className={styles.label}>МАССА</span>
          <span className={styles.metric_value}>
            {hasValue(task.weight) ? `${task.weight} тонн` : NO_DATA.LONG_DASH}
          </span>
        </div>
        <div className={styles.metric}>
          <span className={styles.label}>ОБЪЁМ</span>
          <span className={styles.metric_value}>{hasValue(task.volume) ? `${task.volume} м³` : NO_DATA.LONG_DASH}</span>
        </div>
      </div>

      <div className={styles.cargo_block}>
        <span className={styles.label}>ГРУЗ</span>
        <span className={styles.cargo_value}>{cargo}</span>
      </div>
    </div>
  );
};
