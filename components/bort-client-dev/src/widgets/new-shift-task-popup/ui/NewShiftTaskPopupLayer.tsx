import { showNotification } from '@mantine/notifications';
import { useEffect, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';

import type { ShiftTaskResponse } from '@/shared/api/endpoints/shift-tasks';
import { useActivateRouteTaskMutation, useCancelRouteTaskMutation } from '@/shared/api/endpoints/tasks';
import type { RouteTaskResponse } from '@/shared/api/endpoints/tasks';
import { useCurrentShiftTasks } from '@/shared/lib/hooks/useCurrentShiftTasks';
import { useShiftTasksSse } from '@/shared/lib/hooks/useShiftTasksSse';
import { getRouteMain } from '@/shared/routes/router';

import { NewShiftTaskPopup } from './NewShiftTaskPopup/NewShiftTaskPopup';

/**
 * Элемент очереди: снимок наряда на момент SSE и новое маршрутное задание для карточки.
 */
interface NewRouteTaskQueueItem {
  /** Снимок наряда на момент получения SSE-события. */
  readonly shiftTask: ShiftTaskResponse;
  /** Новое маршрутное задание для отображения в попапе. */
  readonly newRouteTask: RouteTaskResponse;
}

/**
 * Подписка на SSE, очередь новых маршрутов и блокирующий попап поверх kiosk.
 */
export const NewShiftTaskPopupLayer = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { data: shiftTasksData, isSuccess: shiftTasksLoaded } = useCurrentShiftTasks();
  const [queue, setQueue] = useState<NewRouteTaskQueueItem[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const seenRouteTaskIdsRef = useRef<Set<string>>(new Set());
  const baselineReadyRef = useRef(false);

  const [activateRouteTask] = useActivateRouteTaskMutation();
  const [cancelRouteTask] = useCancelRouteTaskMutation();

  useShiftTasksSse();

  useEffect(() => {
    if (!shiftTasksLoaded) {
      return;
    }
    const shift = shiftTasksData?.items?.[0];
    if (!shift) {
      return;
    }

    const rts = shift.route_tasks ?? [];

    if (!baselineReadyRef.current) {
      for (const rt of rts) {
        seenRouteTaskIdsRef.current.add(rt.id);
      }
      baselineReadyRef.current = true;
      return;
    }

    setQueue((prev) => {
      const next = [...prev];
      for (const rt of rts) {
        if (!seenRouteTaskIdsRef.current.has(rt.id)) {
          seenRouteTaskIdsRef.current.add(rt.id);
          next.push({ shiftTask: shift, newRouteTask: rt });
        }
      }
      return next;
    });
  }, [shiftTasksLoaded, shiftTasksData]);

  const current = queue[0] ?? null;

  const handleConfirm = async () => {
    if (!current) {
      return;
    }
    setIsSubmitting(true);
    try {
      await activateRouteTask({ taskId: current.newRouteTask.id }).unwrap();
      setQueue((q) => q.slice(1));
      const mainRoute = getRouteMain();
      if (location.pathname !== mainRoute) {
        void navigate(mainRoute);
      }
    } catch {
      showNotification({
        title: 'Ошибка',
        message: 'Не удалось принять задание.',
        color: 'red',
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleReject = async () => {
    if (!current) {
      return;
    }
    setIsSubmitting(true);
    try {
      await Promise.all(current.shiftTask.route_tasks.map((rt) => cancelRouteTask({ taskId: rt.id }).unwrap()));
      const shiftId = current.shiftTask.id;
      setQueue((q) => q.filter((item) => item.shiftTask.id !== shiftId));
    } catch {
      showNotification({
        title: 'Ошибка',
        message: 'Не удалось отказаться от задания.',
        color: 'red',
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!current) {
    return null;
  }

  return (
    <NewShiftTaskPopup
      key={current.newRouteTask.id}
      routeTask={current.newRouteTask}
      onConfirm={handleConfirm}
      onReject={handleReject}
      isLoading={isSubmitting}
    />
  );
};
