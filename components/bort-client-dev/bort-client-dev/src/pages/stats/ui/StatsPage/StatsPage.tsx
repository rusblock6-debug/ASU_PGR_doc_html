import { useEffect } from 'react';

import {
  getCargoLabel,
  getPlaceLabelFromRouteData,
  getRouteStatusLabel,
  getRouteStatusVariant,
  isRouteTaskFinished,
  isRouteTaskInProgress,
  useRouteTaskPlaceNames,
} from '@/entities/route-task';

import { useGetCurrentShiftStatsQuery } from '@/shared/api';
import type { CurrentShiftStatsResponse } from '@/shared/api/types/current-shift-stats';
import type { RouteTaskResponse } from '@/shared/api/types/trip-service';
import { VEHICLE_ID_STR } from '@/shared/config/env';
import { cn } from '@/shared/lib/classnames-utils';
import { NO_DATA } from '@/shared/lib/constants';
import { useCargoMetrics } from '@/shared/lib/hooks/useCargoMetrics';
import { useCurrentShiftTasks } from '@/shared/lib/hooks/useCurrentShiftTasks';
import { useKioskNavigation } from '@/shared/lib/kiosk-navigation';

import styles from './StatsPage.module.css';

const VARIANT_CLASS_MAP: Record<string, string | undefined> = {
  active: styles.status_active,
  done: styles.status_done,
  cancelled: styles.status_cancelled,
  paused: styles.status_paused,
};

const TIME_HH_MM_RE = /(\d{2}:\d{2})/;

/** Строка времени ЧЧ:ММ из полей `route_data` или полная строка без разбора. */
const getTimeStrFromValue = (value: string | null | undefined) => {
  if (typeof value !== 'string' || !value.trim()) return NO_DATA.LONG_DASH;
  const match = TIME_HH_MM_RE.exec(value);
  if (match) return match[1];
  return value.trim();
};

/** Строка времени ЧЧ:ММ из полей `route_data` или полная строка без разбора. */
const getTimeStr = (data: Record<string, unknown> | null, ...keys: string[]) => {
  if (!data) return NO_DATA.LONG_DASH;
  for (const key of keys) {
    const resolved = getTimeStrFromValue(typeof data[key] === 'string' ? data[key] : undefined);
    if (resolved !== NO_DATA.LONG_DASH) return resolved;
  }
  return NO_DATA.LONG_DASH;
};

/** Пропсы блока сводки смены (GET /api/event-log/current-shift-stats). */
interface SummaryProps {
  readonly stats: CurrentShiftStatsResponse | undefined;
  readonly isLoading: boolean;
  readonly isError: boolean;
}

/** Сетка агрегатов по смене из event-log (над таблицей). */
const StatsSummary = ({ stats, isLoading, isError }: SummaryProps) => {
  const cell = (resolve: (s: CurrentShiftStatsResponse) => string) => {
    if (isLoading) return NO_DATA.ELLIPSIS;
    if (isError || !stats) return NO_DATA.LONG_DASH;
    return resolve(stats);
  };

  const subFrac = (plannedKey: keyof CurrentShiftStatsResponse) => {
    if (isLoading || isError || !stats) return undefined;
    const n = stats[plannedKey];
    return `/${String(n)}`;
  };

  const tripsHighlight =
    stats != null && stats.planned_trips_count_sum > 0 && stats.actual_trips_count_sum < stats.planned_trips_count_sum;
  const weightHighlight =
    stats != null && stats.planned_weight_sum > 0 && stats.actual_weight_sum < stats.planned_weight_sum;

  const items = [
    { label: 'ЭФ.ВРЕМЯ, МИН', value: cell((s) => String(s.work_time_sum)) },
    { label: 'ПРОСТОИ, МИН', value: cell((s) => String(s.idle_time_sum)) },
    { label: 'ПУТЬ, КМ', value: NO_DATA.DASH },
    {
      label: 'РЕЙСЫ, ШТ.',
      value: cell((s) => String(s.actual_trips_count_sum)),
      subValue: subFrac('planned_trips_count_sum'),
      highlight: tripsHighlight,
    },
    { label: 'ТОПЛИВО, Л', value: NO_DATA.DASH },
    {
      label: 'ВЕС, Т',
      value: cell((s) => String(s.actual_weight_sum)),
      subValue: subFrac('planned_weight_sum'),
      highlight: weightHighlight,
    },
  ];

  return (
    <div className={styles.summary}>
      {items.map((item) => (
        <div
          key={item.label}
          className={styles.summary_item}
        >
          <span className={styles.summary_label}>{item.label}</span>
          <span className={styles.summary_value}>
            <span className={item.highlight ? styles.summary_value_warn : undefined}>{item.value}</span>
            {item.subValue ? <span className={styles.summary_value_sub}>{item.subValue}</span> : null}
          </span>
        </div>
      ))}
    </div>
  );
};

/** Пропсы строки таблицы маршрутов. */
interface TaskRowProps {
  readonly index: number;
  readonly task: RouteTaskResponse;
  readonly shiftStartedAt?: string | null;
  readonly shiftCompletedAt?: string | null;
}

/** Одна строка таблицы: маршрут, груз, рейсы, вес, время, статус. */
const StatsTaskRow = ({ index, task, shiftStartedAt, shiftCompletedAt }: TaskRowProps) => {
  const { placeAName, placeBName } = useRouteTaskPlaceNames(task.place_a_id, task.place_b_id);
  const { cargoTypeName } = useCargoMetrics(task.place_b_id);
  const variant = getRouteStatusVariant(task.status);
  const start = getPlaceLabelFromRouteData(task.place_a_id, task.route_data, 'place_a_name', placeAName);
  const end = getPlaceLabelFromRouteData(task.place_b_id, task.route_data, 'place_b_name', placeBName);
  const cargoLabel = getCargoLabel(task.type_task, task.route_data, cargoTypeName);
  const statusLabel = getRouteStatusLabel(task.status);
  const shouldShowStartTime = isRouteTaskInProgress(task.status) || isRouteTaskFinished(task.status);
  const shouldShowEndTime = isRouteTaskFinished(task.status);
  const startTimeFromRoute = shouldShowStartTime
    ? getTimeStr(task.route_data, 'start_time', 'begin_time', 'started_at', 'time_start', 'planned_start')
    : NO_DATA.LONG_DASH;
  const endTimeFromRoute = shouldShowEndTime
    ? getTimeStr(task.route_data, 'end_time', 'finish_time', 'completed_at', 'time_end', 'planned_end')
    : NO_DATA.LONG_DASH;
  const startTime = startTimeFromRoute !== NO_DATA.LONG_DASH ? startTimeFromRoute : getTimeStrFromValue(shiftStartedAt);
  const endTime = endTimeFromRoute !== NO_DATA.LONG_DASH ? endTimeFromRoute : getTimeStrFromValue(shiftCompletedAt);

  return (
    <div className={styles.row}>
      <span>{index + 1}</span>
      <span>{start}</span>
      <span>{end}</span>
      <span className={styles.cell_cargo}>{cargoLabel}</span>
      <span>
        {task.actual_trips_count}/{task.planned_trips_count}
      </span>
      <span>{task.weight != null ? String(task.weight) : NO_DATA.LONG_DASH}</span>
      <span>{startTime}</span>
      <span>{endTime}</span>
      <span className={cn(VARIANT_CLASS_MAP[variant] ?? styles.status_waiting)}>{statusLabel}</span>
    </div>
  );
};

/** Экран статистики смены: сводка и таблица маршрутов наряда. */
export const StatsPage = () => {
  const { data, isLoading, error } = useCurrentShiftTasks();
  const {
    data: shiftStats,
    isLoading: isShiftStatsLoading,
    isError: isShiftStatsError,
  } = useGetCurrentShiftStatsQuery(VEHICLE_ID_STR);
  const { setItemIds, setOnConfirm } = useKioskNavigation();

  useEffect(() => {
    setItemIds([]);
    setOnConfirm(null);
  }, [setItemIds, setOnConfirm]);

  if (isLoading) {
    return <div className={styles.loading}>Загрузка статистики…</div>;
  }

  if (error) {
    return <div className={styles.error}>Не удалось загрузить данные.</div>;
  }

  const shift = data?.items?.[0] ?? null;
  const tasks = [...(shift?.route_tasks ?? [])].sort((a, b) => a.route_order - b.route_order);

  return (
    <div className={styles.page}>
      <StatsSummary
        stats={shiftStats}
        isLoading={isShiftStatsLoading}
        isError={isShiftStatsError}
      />
      <div className={styles.table}>
        <div className={styles.header}>
          <span>№</span>
          <span>НАЧАЛО МАРШРУТА</span>
          <span>КОНЕЦ МАРШРУТА</span>
          <span>ТИП ГРУЗА</span>
          <span>РЕЙСЫ</span>
          <span>ВЕС, Т</span>
          <span>НАЧАЛО</span>
          <span>ОКОНЧ.</span>
          <span>СТАТУС</span>
        </div>
        {tasks.length === 0 ? (
          <div className={styles.empty}>Нет маршрутов в наряде</div>
        ) : (
          tasks.map((task, i) => (
            <StatsTaskRow
              key={task.id}
              index={i}
              task={task}
              shiftStartedAt={shift?.started_at}
              shiftCompletedAt={shift?.completed_at}
            />
          ))
        )}
      </div>
    </div>
  );
};
