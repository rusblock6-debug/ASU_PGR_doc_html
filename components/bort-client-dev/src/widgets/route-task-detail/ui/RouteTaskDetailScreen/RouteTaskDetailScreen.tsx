import { RouteTaskActionPanel } from '@/features/route-task-actions';

import { RouteTaskDetail } from '@/entities/route-task';

import type { RouteTaskResponse } from '@/shared/api/endpoints/tasks';
import { useRouteNodeMetrics } from '@/shared/lib/hooks/useRouteNodeMetrics';

import styles from './RouteTaskDetailScreen.module.css';

/**
 * Пропсы экрана деталей маршрутного задания.
 */
interface RouteTaskDetailScreenProps {
  /** Маршрутное задание для отображения деталей. */
  readonly task: RouteTaskResponse;
}

/**
 * Экран деталей маршрута: панель действий и карточка параметров.
 */
export const RouteTaskDetailScreen = ({ task }: RouteTaskDetailScreenProps) => {
  const { distanceLabel, durationLabel } = useRouteNodeMetrics(task.place_a_id, task.place_b_id);

  return (
    <div className={styles.root}>
      <div className={styles.body}>
        <RouteTaskActionPanel task={task} />
        <div className={styles.main}>
          <RouteTaskDetail
            task={task}
            distanceLabel={distanceLabel}
            durationLabel={durationLabel}
          />
        </div>
      </div>
    </div>
  );
};
