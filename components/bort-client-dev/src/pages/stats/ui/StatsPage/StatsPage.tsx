import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import {
  getCargoLabel,
  getPlaceLabelFromRouteData,
  getRouteStatusLabel,
  getRouteStatusVariant,
  useRouteTaskPlaceNames,
} from '@/entities/route-task';

import type { CurrentShiftStatsResponse } from '@/shared/api/endpoints/event-log';
import { useGetCurrentShiftStatsQuery } from '@/shared/api/endpoints/event-log';
import type { RouteTaskResponse } from '@/shared/api/endpoints/tasks';
import { useUpdateRouteTaskMutation } from '@/shared/api/endpoints/tasks';
import { VEHICLE_ID_STR } from '@/shared/config/env';
import { useAuth } from '@/shared/lib/auth';
import { cn } from '@/shared/lib/classnames-utils';
import { NO_DATA } from '@/shared/lib/constants';
import { formatMetric } from '@/shared/lib/format-metric';
import { hasValue, hasValueNotEmpty } from '@/shared/lib/has-value';
import { useCargoMetrics } from '@/shared/lib/hooks/useCargoMetrics';
import { useCurrentShiftTasks } from '@/shared/lib/hooks/useCurrentShiftTasks';
import { useKioskNavigation } from '@/shared/lib/kiosk-navigation';
import { getRouteLogin } from '@/shared/routes/router';

import styles from './StatsPage.module.css';

const VARIANT_CLASS_MAP: Record<string, string | undefined> = {
  active: styles.status_active,
  done: styles.status_done,
  cancelled: styles.status_cancelled,
  paused: styles.status_paused,
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

  type PlannedFractionKey = 'planned_trips_count_sum' | 'planned_volume_sum' | 'planned_weight_sum';

  const subFrac = (plannedKey: PlannedFractionKey) => {
    if (isLoading || isError || !stats) return undefined;
    return `/${formatMetric(stats[plannedKey])}`;
  };

  const tripsHighlight =
    hasValue(stats) &&
    stats.planned_trips_count_sum > 0 &&
    stats.actual_trips_count_sum < stats.planned_trips_count_sum;
  const volumeHighlight =
    hasValue(stats) && stats.planned_volume_sum > 0 && stats.actual_volume_sum < stats.planned_volume_sum;
  const weightHighlight =
    hasValue(stats) && stats.planned_weight_sum > 0 && stats.actual_weight_sum < stats.planned_weight_sum;

  const metricPair = (
    actualKey: 'actual_volume_sum' | 'actual_weight_sum',
    plannedKey: 'planned_volume_sum' | 'planned_weight_sum',
  ) => {
    if (isLoading) return { value: NO_DATA.ELLIPSIS, subValue: undefined as string | undefined };
    if (isError || !stats) return { value: NO_DATA.LONG_DASH, subValue: undefined };
    return {
      value: formatMetric(stats[actualKey]),
      subValue: subFrac(plannedKey),
    };
  };

  const volumePair = metricPair('actual_volume_sum', 'planned_volume_sum');
  const weightPair = metricPair('actual_weight_sum', 'planned_weight_sum');

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
    {
      label: 'ОБЪЁМ, М³',
      value: volumePair.value,
      subValue: volumePair.subValue,
      highlight: volumeHighlight,
    },
    { label: 'ТОПЛИВО, Л', value: NO_DATA.DASH },
    {
      label: 'ВЕС, Т',
      value: weightPair.value,
      subValue: weightPair.subValue,
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
  readonly isSelected: boolean;
  readonly rowRef?: (el: HTMLDivElement | null) => void;
}

/** Одна строка таблицы: маршрут, груз, рейсы, вес и статус. */
const StatsTaskRow = ({ index, task, isSelected, rowRef }: TaskRowProps) => {
  const { placeAName, placeBName } = useRouteTaskPlaceNames(task.place_a_id, task.place_b_id);
  const { cargoTypeName } = useCargoMetrics(task.place_b_id);
  const variant = getRouteStatusVariant(task.status);
  const start = getPlaceLabelFromRouteData(task.place_a_id, task.route_data, 'place_a_name', placeAName);
  const end = getPlaceLabelFromRouteData(task.place_b_id, task.route_data, 'place_b_name', placeBName);
  const cargoLabel = getCargoLabel(task.type_task, task.route_data, cargoTypeName);
  const statusLabel = getRouteStatusLabel(task.status);

  return (
    <div
      ref={rowRef}
      className={cn(styles.row, isSelected && styles.row_selected)}
    >
      <span>{index + 1}</span>
      <span>{start}</span>
      <span>{end}</span>
      <span className={styles.cell_cargo}>{cargoLabel}</span>
      <span>
        {task.actual_trips_count}/{task.planned_trips_count}
      </span>
      <span>{hasValueNotEmpty(task.weight) ? String(task.weight) : NO_DATA.LONG_DASH}</span>
      <span>{hasValueNotEmpty(task.volume) ? String(task.volume) : NO_DATA.LONG_DASH}</span>
      <span className={cn(VARIANT_CLASS_MAP[variant] ?? styles.status_waiting)}>{statusLabel}</span>
    </div>
  );
};

/** Экран статистики смены: сводка и таблица маршрутов наряда. */
export const StatsPage = () => {
  const navigate = useNavigate();
  const { logout } = useAuth();
  const { data, isLoading, error } = useCurrentShiftTasks();
  const [updateRouteTask, { isLoading: isTaskUpdating }] = useUpdateRouteTaskMutation();
  const {
    data: shiftStats,
    isLoading: isShiftStatsLoading,
    isError: isShiftStatsError,
  } = useGetCurrentShiftStatsQuery(VEHICLE_ID_STR);
  const { setItemIds, setOnConfirm, selectedIndex, selectedId } = useKioskNavigation();
  const rowRefs = useRef<(HTMLDivElement | null)[]>([]);
  const [isConfirmExitStep, setIsConfirmExitStep] = useState(false);

  const shift = data?.items?.[0] ?? null;
  const tasksCount = shift?.route_tasks?.length ?? 0;

  useEffect(() => {
    rowRefs.current.length = tasksCount;
  }, [tasksCount]);
  const tasks = useMemo(
    () => [...(shift?.route_tasks ?? [])].sort((a, b) => a.route_order - b.route_order),
    [shift?.route_tasks],
  );
  const taskIds = useMemo(() => tasks.map((task) => task.id), [tasks]);
  const selectedTaskId = selectedId && taskIds.includes(selectedId) ? selectedId : (taskIds[0] ?? null);

  const handleFinishShift = useCallback(() => {
    if (isTaskUpdating) {
      return;
    }
    setIsConfirmExitStep(true);
  }, [isTaskUpdating]);

  const handleConfirmExit = useCallback(async () => {
    if (!selectedTaskId || isTaskUpdating) {
      return;
    }
    await updateRouteTask({ taskId: selectedTaskId, body: { status: 'COMPLETED' } }).unwrap();
    logout();
    void navigate(getRouteLogin(), { replace: true });
  }, [isTaskUpdating, logout, navigate, selectedTaskId, updateRouteTask]);

  const handleExitAction = useCallback(() => {
    if (isConfirmExitStep) {
      void handleConfirmExit();
      return;
    }
    handleFinishShift();
  }, [handleConfirmExit, handleFinishShift, isConfirmExitStep]);

  useEffect(() => {
    setOnConfirm(() => {
      handleExitAction();
    });
    return () => {
      setOnConfirm(null);
    };
  }, [handleExitAction, setOnConfirm]);

  useEffect(() => {
    setItemIds(taskIds);
  }, [setItemIds, taskIds]);

  useEffect(() => {
    if (selectedIndex >= 0 && selectedIndex < rowRefs.current.length) {
      rowRefs.current[selectedIndex]?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    }
  }, [selectedIndex]);

  if (isLoading) {
    return <div className={styles.loading}>Загрузка статистики…</div>;
  }

  if (error) {
    return <div className={styles.error}>Не удалось загрузить данные.</div>;
  }

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
          <span>ОБЪЁМ, М³</span>
          <span>СТАТУС</span>
        </div>
        <div className={styles.table_body}>
          {tasks.length === 0 ? (
            <div className={styles.empty}>Нет маршрутов в наряде</div>
          ) : (
            tasks.map((task, i) => (
              <StatsTaskRow
                key={task.id}
                index={i}
                task={task}
                isSelected={i === selectedIndex}
                rowRef={(el) => {
                  rowRefs.current[i] = el;
                }}
              />
            ))
          )}
        </div>
      </div>
      <button
        type="button"
        className={styles.exit_button}
        disabled={!selectedTaskId || isTaskUpdating}
        onClick={handleExitAction}
      >
        {isConfirmExitStep ? 'ПОДТВЕРДИТЬ ВЫХОД' : 'ЗАВЕРШИТЬ СМЕНУ'}
      </button>
    </div>
  );
};
