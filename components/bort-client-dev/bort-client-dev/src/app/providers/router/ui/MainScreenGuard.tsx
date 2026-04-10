import { Navigate } from 'react-router-dom';

import { MainScreenPage } from '@/pages/main-screen';

import { useGetActiveTaskQuery } from '@/shared/api';
import { extractActiveRouteTaskIdFromPayload } from '@/shared/lib/active-route-task';
import { useCurrentShiftTasks } from '@/shared/lib/hooks/useCurrentShiftTasks';
import { getRouteWorkOrders } from '@/shared/routes/router';

/**
 * Проверяет наличие активного задания в произвольном ответе /active/task.
 */
const hasActiveTask = (raw: unknown) => extractActiveRouteTaskIdFromPayload(raw) != null;

/**
 * Гард главного экрана: при наличии заданий и отсутствии активного переводит в список нарядов.
 */
export const MainScreenGuard = () => {
  const { data, isLoading, error } = useCurrentShiftTasks();
  const { data: activeTaskData, isLoading: isActiveTaskLoading } = useGetActiveTaskQuery();
  const tasks = data?.items?.[0]?.route_tasks ?? [];
  const activeTaskExists = hasActiveTask(activeTaskData);

  if (isLoading || isActiveTaskLoading) {
    return null;
  }

  if (error) {
    return <MainScreenPage />;
  }

  if (tasks.length > 0 && !activeTaskExists) {
    return (
      <Navigate
        to={getRouteWorkOrders()}
        replace
      />
    );
  }

  return <MainScreenPage />;
};
