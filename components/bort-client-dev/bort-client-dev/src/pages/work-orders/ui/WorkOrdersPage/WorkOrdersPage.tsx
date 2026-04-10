import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

import { RouteTaskList } from '@/widgets/route-task-list';

import { useCurrentShiftTasks } from '@/shared/lib/hooks/useCurrentShiftTasks';
import { useKioskNavigation } from '@/shared/lib/kiosk-navigation';
import { getRouteWorkOrderDetail } from '@/shared/routes/router';

import styles from './WorkOrdersPage.module.css';

/**
 * Наряд-задания: список маршрутов с переходом на отдельный роут деталей.
 */
export const WorkOrdersPage = () => {
  const navigate = useNavigate();
  const { data, isLoading, error } = useCurrentShiftTasks();

  const shift = data?.items?.[0] ?? null;
  const tasks = !shift?.route_tasks?.length ? [] : [...shift.route_tasks].sort((a, b) => a.route_order - b.route_order);
  const taskIds = tasks.map((t) => t.id);

  const { setItemIds, setOnConfirm, selectedId, selectedIndex, setSelectedIndex } = useKioskNavigation();

  useEffect(() => {
    setItemIds(taskIds);
  }, [taskIds, setItemIds]);

  useEffect(() => {
    setOnConfirm(() => {
      if (selectedId) {
        void navigate(getRouteWorkOrderDetail(selectedId));
      }
    });
    return () => {
      setOnConfirm(null);
    };
  }, [navigate, selectedId, setOnConfirm]);

  if (isLoading) {
    return <div className={styles.loading}>Загрузка наряд-заданий…</div>;
  }

  if (error) {
    return <div className={styles.error}>Не удалось загрузить данные. Проверьте proxy и Trip Service.</div>;
  }

  return (
    <div className={styles.page}>
      <RouteTaskList
        tasks={tasks}
        selectedIndex={selectedIndex}
        onRowSelect={(index) => {
          setSelectedIndex(index);
          const id = tasks[index]?.id;
          if (id) {
            void navigate(getRouteWorkOrderDetail(id));
          }
        }}
      />
    </div>
  );
};
