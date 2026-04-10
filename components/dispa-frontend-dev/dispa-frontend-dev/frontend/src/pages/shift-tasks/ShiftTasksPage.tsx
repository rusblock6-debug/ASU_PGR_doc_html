/**
 * Страница списка заданий на смену
 */
import { useCallback, useEffect, useState } from 'react';
import {
  tripServiceApi,
  RouteTaskResponse,
  ShiftTaskResponse,
} from '@/shared/api/tripServiceApi';
import { graphServiceApi } from '@/shared/api/graphServiceApi';
import { TestDataImportModal } from './TestDataImportModal';
import './ShiftTasksPage.css';

interface RouteTaskView {
  shift: ShiftTaskResponse;
  route: RouteTaskResponse;
}

export const ShiftTasksPage = () => {
  const [routeTasks, setRouteTasks] = useState<RouteTaskView[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTaskId, setActiveTaskId] = useState<string | null>(null);
  const [activatingTaskId, setActivatingTaskId] = useState<string | null>(null);
  const [activeTaskCompletedTrips, setActiveTaskCompletedTrips] = useState<number>(0);
  const [placesMap, setPlacesMap] = useState<Record<string, string>>({});

  // Загрузить задания на смену
  const loadShiftTasks = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const [shiftTasksData, activeTask] = await Promise.all([
        tripServiceApi.getShiftTasks({
          page: 1,
          size: 100,
        }),
        tripServiceApi.getActiveTask(),
      ]);

      const flattenedRouteTasks: RouteTaskView[] = shiftTasksData.items.flatMap((shift) =>
        shift.route_tasks.map((route) => ({
          shift,
          route,
        }))
      );

      setRouteTasks(flattenedRouteTasks);
      const taskId = activeTask?.task_id ?? null;
      setActiveTaskId(taskId);

      // Загрузить количество завершенных рейсов для активного задания
      if (taskId) {
        try {
          const completedTrips = await tripServiceApi.getCompletedTripsCount(taskId);
          setActiveTaskCompletedTrips(completedTrips);
        } catch (tripCountErr) {
          console.error('Failed to load completed trips count:', tripCountErr);
          setActiveTaskCompletedTrips(0);
        }
      } else {
        setActiveTaskCompletedTrips(0);
      }
    } catch (err: any) {
      console.error('Failed to load tasks:', err);
      setError('Ошибка загрузки заданий');
    } finally {
      setLoading(false);
    }
  }, []);

  const handleActivateRoute = useCallback(
    async (routeId: string) => {
      if (activatingTaskId === routeId || loading) {
        return;
      }

      setActivatingTaskId(routeId);
      setError(null);

      try {
        await tripServiceApi.activateTask(routeId);
        await loadShiftTasks();
      } catch (err: any) {
        console.error('Failed to activate task:', err);
        const message =
          err?.response?.data?.detail ||
          err?.response?.data?.message ||
          err?.message ||
          'Не удалось активировать задание';
        setError(message);
      } finally {
        setActivatingTaskId(null);
      }
    },
    [activatingTaskId, loading, loadShiftTasks]
  );

  // Получить статус задания для отображения
  const getTaskStatusLabel = (routeTask: RouteTaskResponse): string => {
    switch (routeTask.status) {
      case 'completed':
        return 'Выполнено';
      case 'in_progress':
      case 'active':
        return 'В работе';
      case 'paused':
        return 'Приостановлено';
      case 'pending':
      default:
        return 'На выполнение';
    }
  };

  // Загрузить места из graph-service
  const loadPlaces = useCallback(async () => {
    try {
      const response = await graphServiceApi.getPlaces({ limit: 1000, offset: 0 });
      const map: Record<string, string> = {};
      response.items.forEach((place) => {
        // Индексируем по place.id (число)
        map[String(place.id)] = place.name;
      });
      setPlacesMap(map);
    } catch (placesError) {
      console.error('Failed to load places:', placesError);
    }
  }, []);

  // Получить название места по place_id
  const getPlaceLabel = useCallback(
    (placeId?: number | null) => {
      if (!placeId) {
        return '—';
      }
      const placeIdStr = String(placeId);
      return placesMap[placeIdStr] || placeIdStr;
    },
    [placesMap],
  );

  // Загрузить задания при монтировании
  useEffect(() => {
    loadShiftTasks();
  }, [loadShiftTasks]);

  // Загрузить места при монтировании
  useEffect(() => {
    loadPlaces();
  }, [loadPlaces]);

  return (
    <div className="shift-tasks-page">
      {/* Заголовок */}
      <div className="page-header">
        <h1>Задания на смену</h1>
        <button className="refresh-button" onClick={loadShiftTasks} disabled={loading}>
          {loading ? 'Загрузка...' : 'Обновить'}
        </button>
      </div>

      {/* Тестовое окно для импорта JSON */}
      <TestDataImportModal onImportSuccess={loadShiftTasks} />

      {/* Ошибка */}
      {error && <div className="error-message">{error}</div>}

      {/* Список заданий */}
      <div className="tasks-list">
        {routeTasks.map(({ shift, route }) => {
          const plannedTrips = route.planned_trips_count ?? 0;
          const isActive = route.id === activeTaskId;
          // Для активного задания используем количество из getCompletedTripsCount, для остальных - из route.actual_trips_count
          const completedTrips = isActive ? activeTaskCompletedTrips : (route.actual_trips_count ?? 0);
          const isCompleted = plannedTrips > 0 && completedTrips >= plannedTrips;

          const isActivating = activatingTaskId === route.id;

          return (
            <div
              key={route.id}
              className={[
                'task-row',
                isCompleted ? 'task-completed' : '',
                isActive ? 'task-row-active' : '',
                isActivating ? 'task-row-loading' : '',
              ]
                .filter(Boolean)
                .join(' ')}
              role="button"
              tabIndex={0}
              onClick={() => handleActivateRoute(route.id)}
              onKeyDown={(event) => {
                if (event.key === 'Enter' || event.key === ' ') {
                  event.preventDefault();
                  handleActivateRoute(route.id);
                }
              }}
            >
              <div className="task-header">
                <span className="task-shift">{shift.task_name}</span>
                <span className="task-date">{shift.shift_date}</span>
              </div>
              <div className="task-route">
                <span className="route-from">{getPlaceLabel(route.place_a_id)}</span>
                <span className="route-arrow">→</span>
                <span className="route-to">{getPlaceLabel(route.place_b_id)}</span>
              </div>
              <div className="task-trips">
                Рейсов: {completedTrips} / {plannedTrips}
              </div>
              <div className="task-volume">
                {route.route_data?.weight && route.route_data?.volume
                  ? `${route.route_data.weight}т / ${route.route_data.volume}м³`
                  : '—'}
              </div>
              <div className="task-message">
                {route.route_data?.message_to_driver || 'Нет сообщения'}
              </div>
              <div className={`task-status status-${route.status}`}>
                {getTaskStatusLabel(route)}
              </div>
            </div>
          );
        })}

        {routeTasks.length === 0 && !loading && (
          <div className="no-tasks">Нет заданий на смену</div>
        )}
      </div>
    </div>
  );
};