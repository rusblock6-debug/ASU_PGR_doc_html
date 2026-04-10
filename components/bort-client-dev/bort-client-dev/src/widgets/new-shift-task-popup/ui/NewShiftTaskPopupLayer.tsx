import { showNotification } from '@mantine/notifications';
import { useEffect, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';

import { useActivateRouteTaskMutation, useCancelRouteTaskMutation } from '@/shared/api';
import type { RouteTaskResponse, ShiftTaskChangedSsePayload, ShiftTaskResponse } from '@/shared/api/types/trip-service';
import { VEHICLE_ID_NUM } from '@/shared/config/env';
import { useCurrentShiftTasks } from '@/shared/lib/hooks/useCurrentShiftTasks';
import { useShiftTasksSse } from '@/shared/lib/hooks/useShiftTasksSse';
import { getRouteMain } from '@/shared/routes/router';

import { NewShiftTaskPopup } from './NewShiftTaskPopup/NewShiftTaskPopup';

/**
 * Элемент очереди: снимок наряда на момент SSE и новое маршрутное задание для карточки.
 */
interface NewRouteTaskQueueItem {
  readonly shiftTask: ShiftTaskResponse;
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

  useEffect(() => {
    if (!shiftTasksLoaded) {
      return;
    }
    const shift = shiftTasksData?.items?.[0];
    if (!shift) {
      return;
    }

    const rts = shift.route_tasks ?? [];

    // Инициализируем "базу" один раз и далее ставим в очередь только реально новые `route_task.id`.
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

  const enqueueFromPayload = (payload: ShiftTaskChangedSsePayload) => {
    if (!baselineReadyRef.current) {
      return;
    }
    if (payload.event_type !== 'shift_task_changed') {
      return;
    }
    if (payload.action !== 'update') {
      return;
    }
    if (payload.vehicle_id !== VEHICLE_ID_NUM) {
      return;
    }
    const st = payload.shift_task;
    if (!st?.route_tasks?.length) {
      return;
    }

    setQueue((prev) => {
      const next = [...prev];
      for (const rt of st.route_tasks) {
        if (!seenRouteTaskIdsRef.current.has(rt.id)) {
          seenRouteTaskIdsRef.current.add(rt.id);
          next.push({ shiftTask: st, newRouteTask: rt });
        }
      }
      return next;
    });
  };

  useShiftTasksSse(enqueueFromPayload);

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
