import { useEffect } from 'react';
import { Navigate, useParams } from 'react-router-dom';

import { RouteTaskDetailScreen } from '@/widgets/route-task-detail';

import { ROUTE_DETAIL_KIOSK_ITEM_IDS } from '@/features/route-task-actions';

import { isRouteTaskFinished } from '@/entities/route-task';

import { useCurrentShiftTasks } from '@/shared/lib/hooks/useCurrentShiftTasks';
import { useKioskNavigation } from '@/shared/lib/kiosk-navigation';
import { getRouteWorkOrders } from '@/shared/routes/router';

import styles from './WorkOrderDetailPage.module.css';

/**
 * Детализация задания по taskId из URL.
 */
export const WorkOrderDetailPage = () => {
  const { taskId } = useParams<{ taskId: string }>();
  const { data, isLoading, error } = useCurrentShiftTasks();
  const { setItemIds } = useKioskNavigation();

  const items = data?.items?.[0]?.route_tasks ?? [];
  const task = taskId ? (items.find((item) => item.id === taskId) ?? null) : null;

  useEffect(() => {
    const isActionPanelDisabled = !task || isRouteTaskFinished(task.status);
    setItemIds(isActionPanelDisabled ? [] : [...ROUTE_DETAIL_KIOSK_ITEM_IDS]);
  }, [setItemIds, task]);

  if (isLoading) {
    return <div className={styles.loading}>Загрузка задания…</div>;
  }

  if (error) {
    return <div className={styles.error}>Не удалось загрузить данные. Проверьте proxy и Trip Service.</div>;
  }

  if (!task) {
    return (
      <Navigate
        to={getRouteWorkOrders()}
        replace
      />
    );
  }

  return (
    <div className={styles.page}>
      <RouteTaskDetailScreen task={task} />
    </div>
  );
};
