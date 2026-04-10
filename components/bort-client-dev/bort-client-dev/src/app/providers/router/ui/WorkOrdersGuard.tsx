import { WorkOrdersPage } from '@/pages/work-orders';

import { useCurrentShiftTasks } from '@/shared/lib/hooks/useCurrentShiftTasks';

/**
 * Гард списка нарядов: если маршрутов нет, возвращает на главный экран.
 */
export const WorkOrdersGuard = () => {
  const { isLoading, error } = useCurrentShiftTasks();

  if (isLoading) {
    return null;
  }

  if (error) {
    return <WorkOrdersPage />;
  }

  return <WorkOrdersPage />;
};
