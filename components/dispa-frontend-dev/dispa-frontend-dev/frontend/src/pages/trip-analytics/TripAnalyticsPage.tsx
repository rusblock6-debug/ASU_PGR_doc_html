/**
 * Страница статистики рейсов - аналитика по завершенным рейсам
 */
import { useEffect, useState } from 'react';
import { tripServiceApi } from '@/shared/api/tripServiceApi';
import './TripAnalyticsPage.css';

interface TripAnalyticsItem {
  id: number;
  internal_trip_id: string;  // Отображаемый ID (cycle_id)
  vehicle_id: string;
  shift_id?: string | null;
  trip_type?: string | null;
  trip_status?: string | null;
  from_point_id?: string | null;
  to_point_id?: string | null;
  trip_started_at?: string | null;
  trip_completed_at?: string | null;
  total_duration_seconds?: number | null;
  moving_empty_duration_seconds?: number | null;
  stopped_empty_duration_seconds?: number | null;
  loading_duration_seconds?: number | null;
  moving_loaded_duration_seconds?: number | null;
  stopped_loaded_duration_seconds?: number | null;
  unloading_duration_seconds?: number | null;
  state_transitions_count?: number | null;
  analytics_data?: any;
  created_at: string;
  updated_at: string;
}

export const TripAnalyticsPage = () => {
  const [analytics, setAnalytics] = useState<TripAnalyticsItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [pages, setPages] = useState(1);
  const pageSize = 20;

  // Загрузить статистику
  const loadAnalytics = async () => {
    setLoading(true);
    setError(null);

    try {
      const params = {
        page,
        size: pageSize,
      };

      const response = await tripServiceApi.getTripAnalytics(params);

      setAnalytics(response.items);
      setTotal(response.total);
      setPages(response.pages);
    } catch (err: any) {
      console.error('Failed to load trip analytics:', err);
      setError('Ошибка загрузки статистики рейсов');
    } finally {
      setLoading(false);
    }
  };

  // Загрузить статистику при изменении страницы
  useEffect(() => {
    loadAnalytics();
  }, [page]);

  // Форматировать дату и время
  const formatDateTime = (timestamp?: string | null): string => {
    if (!timestamp) return '-';
    const date = new Date(timestamp);
    return date.toLocaleString('ru-RU', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  };

  // Форматировать длительность в минуты и секунды
  const formatDuration = (seconds?: number | null): string => {
    if (seconds === null || seconds === undefined) return '-';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}м ${secs}с`;
  };

  // Получить текст типа рейса
  const getTripTypeText = (type?: string | null): string => {
    const typeMap: Record<string, string> = {
      planned: 'Плановый',
      unplanned: 'Внеплановый',
    };
    return typeMap[type || ''] || type || '-';
  };

  // Получить текст статуса рейса
  const getTripStatusText = (status?: string | null): string => {
    const statusMap: Record<string, string> = {
      completed: 'Завершен',
      in_progress: 'В процессе',
      cancelled: 'Отменен',
    };
    return statusMap[status || ''] || status || '-';
  };

  return (
    <div className="trip-analytics-page">
      <h1>Статистика рейсов</h1>

      {/* Статус загрузки */}
      {loading && <div className="loading">Загрузка...</div>}
      {error && <div className="error">{error}</div>}

      {/* Таблица статистики */}
      {!loading && !error && (
        <>
          <div className="analytics-summary">
            <span>Всего записей: {total}</span>
            <span>Страница {page} из {pages}</span>
          </div>

          <div className="table-container">
            <table className="analytics-table">
              <thead>
                <tr>
                  <th>ID рейса</th>
                  <th>Тип</th>
                  <th>Статус</th>
                  <th>Начало</th>
                  <th>Завершение</th>
                  <th>Общая длит.</th>
                  <th>Движ. порожн.</th>
                  <th>Ост. порожн.</th>
                  <th>Погрузка</th>
                  <th>Движ. груж.</th>
                  <th>Ост. груж.</th>
                  <th>Разгрузка</th>
                  <th>Переходы</th>
                </tr>
              </thead>
              <tbody>
                {analytics.length === 0 ? (
                  <tr>
                    <td colSpan={13} className="no-data">
                      Нет данных
                    </td>
                  </tr>
                ) : (
                  analytics.map((item) => (
                    <tr key={item.id}>
                      <td className="trip-id">{item.internal_trip_id}</td>
                      <td>{getTripTypeText(item.trip_type)}</td>
                      <td>{getTripStatusText(item.trip_status)}</td>
                      <td className="timestamp">{formatDateTime(item.trip_started_at)}</td>
                      <td className="timestamp">{formatDateTime(item.trip_completed_at)}</td>
                      <td className="duration">{formatDuration(item.total_duration_seconds)}</td>
                      <td className="duration">{formatDuration(item.moving_empty_duration_seconds)}</td>
                      <td className="duration">{formatDuration(item.stopped_empty_duration_seconds)}</td>
                      <td className="duration">{formatDuration(item.loading_duration_seconds)}</td>
                      <td className="duration">{formatDuration(item.moving_loaded_duration_seconds)}</td>
                      <td className="duration">{formatDuration(item.stopped_loaded_duration_seconds)}</td>
                      <td className="duration">{formatDuration(item.unloading_duration_seconds)}</td>
                      <td className="transitions">{item.state_transitions_count ?? '-'}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* Пагинация */}
          {pages > 1 && (
            <div className="pagination">
              <button
                className="pagination-button"
                disabled={page === 1}
                onClick={() => setPage(page - 1)}
              >
                ← Предыдущая
              </button>
              <span className="pagination-info">
                Страница {page} из {pages}
              </span>
              <button
                className="pagination-button"
                disabled={page === pages}
                onClick={() => setPage(page + 1)}
              >
                Следующая →
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
};
