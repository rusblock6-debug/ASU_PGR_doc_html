import { useEffect } from 'react';
import { useSelector } from 'react-redux';
import { useNavigate } from 'react-router-dom';

import { ActiveRoutePanel } from '@/widgets/active-route-panel';
import { BottomNav } from '@/widgets/bottom-nav';
import { StatusBar } from '@/widgets/status-bar';
import { TripGauge } from '@/widgets/trip-gauge';

import { useGetActiveTaskQuery } from '@/shared/api';
import type { RouteTaskResponse } from '@/shared/api/types/trip-service';
import { resolveActiveRouteTaskForMainScreen } from '@/shared/lib/active-route-task';
import { useCargoMetrics } from '@/shared/lib/hooks/useCargoMetrics';
import { useCurrentShiftTasks } from '@/shared/lib/hooks/useCurrentShiftTasks';
import { useRouteNodeMetrics } from '@/shared/lib/hooks/useRouteNodeMetrics';
import { useRoutesStreamSse } from '@/shared/lib/hooks/useRoutesStreamSse';
import { useStateElapsedTimer } from '@/shared/lib/hooks/useStateElapsedTimer';
import { useKioskNavigation } from '@/shared/lib/kiosk-navigation';
import { selectRouteStreamDistanceMeters, selectRouteStreamDurationSeconds } from '@/shared/lib/route-stream';
import { selectVehicleState, selectWeightValue } from '@/shared/lib/vehicle-events';
import { getRouteStats, getRouteVehicleStatus, getRouteWorkOrderDetail } from '@/shared/routes/router';

import styles from './MainScreenPage.module.css';

/**
 * Стабильно сортирует задания по route_order.
 */
const sortByOrder = (tasks: RouteTaskResponse[]) => [...tasks].sort((a, b) => a.route_order - b.route_order);

/** Кнопка в шапке для перехода на экран статистики смены. */
const StatsButton = ({ onClick }: { onClick: () => void }) => (
  <button
    type="button"
    className={styles.system_button}
    aria-label="Статистика"
    onClick={onClick}
  >
    <svg
      viewBox="0 0 24 24"
      className={styles.system_icon}
      aria-hidden
    >
      <path d="M4 20V12M10 20V6M16 20V10M22 20V4" />
    </svg>
  </button>
);

/** Главный экран kiosk-интерфейса с активным маршрутом. */
export const MainScreenPage = () => {
  const navigate = useNavigate();
  const { data: shiftData, isLoading, error } = useCurrentShiftTasks({ refetchOnMountOrArgChange: true });
  const { data: activeTaskData } = useGetActiveTaskQuery(undefined, { refetchOnMountOrArgChange: true });
  const { setItemIds, setOnConfirm } = useKioskNavigation();

  useRoutesStreamSse();

  const stateElapsed = useStateElapsedTimer();
  const streamStateStatus = useSelector(selectVehicleState);
  const weightValue = useSelector(selectWeightValue);
  const sseDistanceM = useSelector(selectRouteStreamDistanceMeters);
  const sseDurationS = useSelector(selectRouteStreamDurationSeconds);

  useEffect(() => {
    setItemIds([]);
    setOnConfirm(null);
  }, [setItemIds, setOnConfirm]);

  const shift = shiftData?.items?.[0] ?? null;
  const tasks = sortByOrder(shift?.route_tasks ?? []);

  const activeTask = resolveActiveRouteTaskForMainScreen(tasks, activeTaskData);

  const plannedTrips = activeTask?.planned_trips_count ?? 0;
  const actualTrips = activeTask?.actual_trips_count ?? 0;

  const { density, cargoTypeName } = useCargoMetrics(activeTask?.place_b_id);

  const { distanceMeters: restDistanceM, durationSeconds: restDurationS } = useRouteNodeMetrics(
    activeTask?.place_a_id ?? 0,
    activeTask?.place_b_id ?? 0,
  );

  const routeStreamDistanceM = sseDistanceM ?? restDistanceM;
  const routeStreamDurationS = sseDurationS ?? restDurationS;

  const streamWeight = weightValue != null ? Number.parseFloat(weightValue.toFixed(2)) : null;
  const streamVolume =
    streamWeight != null && density != null ? Number.parseFloat((streamWeight / density).toFixed(2)) : null;

  if (isLoading) {
    return <div className={styles.loading}>Загрузка главного экрана…</div>;
  }

  if (error) {
    return <div className={styles.error}>Не удалось загрузить данные главного экрана.</div>;
  }

  const currentTaskDetailButton = (
    <button
      type="button"
      className={styles.system_button}
      disabled={!activeTask?.id}
      aria-label="Детали текущего задания"
      onClick={() => {
        if (activeTask?.id) {
          void navigate(getRouteWorkOrderDetail(activeTask.id));
        }
      }}
    >
      <svg
        viewBox="0 0 24 24"
        className={styles.system_icon}
        aria-hidden
      >
        <path d="M9 4.5h6M9 3h6a1.5 1.5 0 0 1 1.5 1.5v1H7.5v-1A1.5 1.5 0 0 1 9 3Z" />
        <path d="M7.5 5.5H6A1.5 1.5 0 0 0 4.5 7v12A1.5 1.5 0 0 0 6 20.5h12a1.5 1.5 0 0 0 1.5-1.5V7A1.5 1.5 0 0 0 18 5.5h-1.5" />
        <path d="M8 10.5h8M8 14h8" />
      </svg>
    </button>
  );

  return (
    <div className={styles.page}>
      <div className={styles.main_columns}>
        <div className={styles.left_column}>
          <div className={styles.left_top}>
            <TripGauge
              key={activeTask?.id ?? 'no-task'}
              actual={actualTrips}
              planned={plannedTrips}
              topLeftAction={<StatsButton onClick={() => navigate(getRouteStats())} />}
              withMovementButton={false}
            />
          </div>
          <div className={styles.left_bottom}>
            <StatusBar
              task={activeTask}
              streamStateStatus={streamStateStatus}
              elapsed={stateElapsed}
              onOpenVehicleStatus={() => void navigate(getRouteVehicleStatus())}
            />
          </div>
        </div>
        <div className={styles.right_column}>
          <div className={styles.right_top}>
            <ActiveRoutePanel
              task={activeTask}
              cargoTypeName={cargoTypeName}
              streamDistanceMeters={routeStreamDistanceM}
              streamDurationSeconds={routeStreamDurationS}
              topRightAction={currentTaskDetailButton}
              streamWeight={streamWeight}
              streamVolume={streamVolume}
            />
          </div>
          <div className={styles.right_bottom}>
            <BottomNav />
          </div>
        </div>
      </div>
    </div>
  );
};
