import { Navigate, useParams } from 'react-router-dom';

import { WorkOrderDetailPage } from '@/pages/work-order-detail';

import { useCurrentShiftTasks } from '@/shared/lib/hooks/useCurrentShiftTasks';
import { getRouteWorkOrders } from '@/shared/routes/router';

/**
 * Гард деталей задания: проверяет, что taskId существует в текущей смене.
 */
export const WorkOrderDetailGuard = () => {
  const { taskId } = useParams<{ taskId: string }>();
  const { data, isLoading, error } = useCurrentShiftTasks();
  const tasks = data?.items?.[0]?.route_tasks ?? [];
  const hasTask = Boolean(taskId && tasks.some((task) => task.id === taskId));

  if (isLoading) {
    return null;
  }

  if (error) {
    return <WorkOrderDetailPage />;
  }

  if (!hasTask) {
    return (
      <Navigate
        to={getRouteWorkOrders()}
        replace
      />
    );
  }

  return <WorkOrderDetailPage />;
};
