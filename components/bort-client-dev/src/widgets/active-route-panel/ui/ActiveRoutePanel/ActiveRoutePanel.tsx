import type React from 'react';

import { getCargoLabel, getPlaceLabelFromRouteData, useRouteTaskPlaceNames } from '@/entities/route-task';

import type { RouteTaskResponse } from '@/shared/api/endpoints/tasks';
import type { VehicleState } from '@/shared/api/types/vehicle-events';
import { NO_DATA } from '@/shared/lib/constants';
import { hasValue } from '@/shared/lib/has-value';
import { getRouteStreamDistanceKmParts, getRouteStreamDurationMinutesParts } from '@/shared/lib/route-stream';

import { RouteConnector } from '../RouteConnector';

import styles from './ActiveRoutePanel.module.css';

/**
 * Пропсы карточки активного маршрута на главном экране.
 */
interface ActiveRoutePanelProps {
  /** Активное маршрутное задание; `null` — нет активного. */
  readonly task: RouteTaskResponse | null;
  /** Имя типа груза из enterprise (graph place → cargo_type). */
  readonly cargoTypeName?: string | null;
  /** Метры до точки из SSE route stream (null — данных ещё нет). */
  readonly streamDistanceMeters?: number | null;
  /** Секунды ETA из SSE (null — данных ещё нет). */
  readonly streamDurationSeconds?: number | null;
  /** Произвольный контент в правом верхнем углу карточки. */
  readonly topRightAction?: React.ReactNode;
  /** Масса из SSE (null — данных нет, берётся из задания). */
  readonly streamWeight?: number | null;
  /** Процент прогресса маршрута из SSE (0–100, null — нет данных). */
  readonly progressPercent?: number | null;
  /** Текущее состояние борта — определяет направление стрелки на коннекторе. */
  readonly vehicleState?: VehicleState | null;
}

/**
 * Пытается извлечь номер маршрута из route_data.
 */
const getRouteNumber = (routeData: RouteTaskResponse['route_data']) => {
  if (!routeData || typeof routeData !== 'object') {
    return NO_DATA.LONG_DASH;
  }

  const candidates = ['route_number', 'route_num', 'route_code', 'number'];
  for (const key of candidates) {
    const value = routeData[key];
    if (typeof value === 'string' && value.trim()) {
      return value;
    }
    if (typeof value === 'number') {
      return String(value);
    }
  }

  return NO_DATA.LONG_DASH;
};

/**
 * Панель текущего активного маршрута.
 */
export const ActiveRoutePanel = ({
  task,
  cargoTypeName,
  streamDistanceMeters = null,
  streamDurationSeconds = null,
  topRightAction,
  streamWeight,
  progressPercent,
  vehicleState,
}: ActiveRoutePanelProps) => {
  const { placeAName, placeBName } = useRouteTaskPlaceNames(task?.place_a_id ?? 0, task?.place_b_id ?? 0, {
    skip: !task,
  });

  if (!task) {
    return (
      <section className={styles.root}>
        <div className={styles.info_rows}>
          <div className={styles.title_row}>
            <h2 className={styles.title}>{NO_DATA.LONG_DASH}</h2>
          </div>
        </div>
      </section>
    );
  }

  const start = getPlaceLabelFromRouteData(task.place_a_id, task.route_data, 'place_a_name', placeAName);
  const end = getPlaceLabelFromRouteData(task.place_b_id, task.route_data, 'place_b_name', placeBName);
  const cargo = getCargoLabel(task.type_task, task.route_data, cargoTypeName);

  const displayWeight = streamWeight ?? task.weight;
  const routeNumber = getRouteNumber(task.route_data);
  const titleMain = routeNumber !== NO_DATA.LONG_DASH ? routeNumber : end;

  const distanceParts = getRouteStreamDistanceKmParts(streamDistanceMeters);
  const durationParts = getRouteStreamDurationMinutesParts(streamDurationSeconds);

  return (
    <section className={styles.root}>
      <RouteConnector
        progressPercent={progressPercent}
        vehicleState={vehicleState}
      />
      {topRightAction ? <div className={styles.top_right}>{topRightAction}</div> : null}
      <div className={styles.info_rows}>
        <div className={styles.title_row}>
          <h2 className={styles.title}>{titleMain}</h2>
        </div>
        <div className={styles.cargo_row}>
          <span className={styles.cargo}>{cargo}</span>
          <span className={styles.weight}>{hasValue(displayWeight) ? `${displayWeight} т` : NO_DATA.LONG_DASH}</span>
        </div>
        <div className={styles.metrics}>
          {distanceParts ? (
            <span className={styles.metric}>
              <span className={styles.metric_tilde}>~</span>
              <span className={styles.metric_num}>{distanceParts.value}</span>
              <span className={styles.metric_unit}>{distanceParts.unit}</span>
            </span>
          ) : (
            <span className={styles.metric}>{NO_DATA.LONG_DASH}</span>
          )}
          {durationParts ? (
            <span className={styles.metric_accent}>
              <span className={styles.metric_tilde}>~</span>
              <span className={styles.metric_num}>{durationParts.value}</span>
              <span className={styles.metric_unit}>{durationParts.unit}</span>
            </span>
          ) : (
            <span className={styles.metric_accent}>{NO_DATA.LONG_DASH}</span>
          )}
        </div>
        <div className={styles.start}>{start}</div>
      </div>
    </section>
  );
};
