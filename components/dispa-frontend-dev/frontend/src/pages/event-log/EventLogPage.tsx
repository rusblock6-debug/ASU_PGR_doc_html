/**
 * Страница журнала событий - история состояний и меток
 */
import { useEffect, useState } from 'react';
import { tripServiceApi } from '@/shared/api/tripServiceApi';
import './EventLogPage.css';

type EventSource = 'state' | 'tag';
type Period = 'hour' | 'shift' | 'day' | 'month';

interface EventItem {
  id: number;
  timestamp: string;
  vehicle_id: string;
  cycle_id?: string | null;  // ID цикла/рейса
  // Для state history
  state?: string;
  state_data?: any;
  trigger_type?: string;
  trigger_data?: any;
  // Для tag history
  point_id?: string;
  tag?: string;
  extra_data?: any;
}

const SHIFT_START = 1;
const SHIFT_END = 3;

const formatDateForQuery = (date: Date): string => {
  return date.toISOString().slice(0, 10);
};

const getDateRangeByPeriod = (period: Period): { fromDate: Date; toDate: Date } => {
  const toDate = new Date();
  const fromDate = new Date(toDate);

  if (period === 'hour') {
    fromDate.setHours(toDate.getHours() - 1);
  } else if (period === 'shift') {
    fromDate.setHours(toDate.getHours() - 8);
  } else if (period === 'day') {
    fromDate.setDate(toDate.getDate() - 1);
  } else {
    fromDate.setMonth(toDate.getMonth() - 1);
  }

  return { fromDate, toDate };
};

export const EventLogPage = () => {
  const [eventSource, setEventSource] = useState<EventSource>('state');
  const [period, setPeriod] = useState<Period>('hour');
  const [events, setEvents] = useState<EventItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [pages, setPages] = useState(1);
  const pageSize = 20;

  // Загрузить события
  const loadEvents = async () => {
    setLoading(true);
    setError(null);

    try {
      const { fromDate, toDate } = getDateRangeByPeriod(period);
      const params = {
        from_date: formatDateForQuery(fromDate),
        to_date: formatDateForQuery(toDate),
        from_shift_num: SHIFT_START,
        to_shift_num: SHIFT_END,
        page,
        size: pageSize,
      };

      let response;
      if (eventSource === 'state') {
        response = await tripServiceApi.getStateHistory(params);
      } else {
        response = await tripServiceApi.getTagHistory(params);
      }

      setEvents(response.items);
      setTotal(response.total);
      setPages(response.pages);
    } catch (err: any) {
      console.error('Failed to load events:', err);
      setError('Ошибка загрузки событий');
    } finally {
      setLoading(false);
    }
  };

  // Загрузить события при изменении фильтров
  useEffect(() => {
    loadEvents();
  }, [eventSource, period, page]);

  // Форматировать дату и время
  const formatDateTime = (timestamp: string): string => {
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

  // Получить текст типа события для state history
  const getEventTypeText = (item: EventItem): string => {
    if (eventSource === 'state') {
      const stateMap: Record<string, string> = {
        idle: 'Ожидание',
        moving_empty: 'Движение порожним',
        stopped_empty: 'Остановка порожним',
        loading: 'Погрузка',
        moving_loaded: 'Движение с грузом',
        stopped_loaded: 'Остановка с грузом',
        unloading: 'Разгрузка',
      };
      return stateMap[item.state || ''] || item.state || '-';
    } else {
      return `Метка: ${item.tag || '-'}`;
    }
  };

  // Получить дополнительную информацию
  const getAdditionalInfo = (item: EventItem): string => {
    if (eventSource === 'state') {
      // Для событий показываем trigger_data
      if (item.trigger_data) {
        try {
          return JSON.stringify(item.trigger_data, null, 2);
        } catch {
          return String(item.trigger_data);
        }
      }
      return '-';
    } else {
      // Для тегов показываем extra_data
      if (item.extra_data) {
        try {
          return JSON.stringify(item.extra_data, null, 2);
        } catch {
          return String(item.extra_data);
        }
      }
      return '-';
    }
  };

  return (
    <div className="event-log-page">
      <h1>Журнал событий</h1>

      {/* Фильтры */}
      <div className="filters">
        <div className="filter-group">
          <label htmlFor="period">Период:</label>
          <select
            id="period"
            value={period}
            onChange={(e) => {
              setPeriod(e.target.value as Period);
              setPage(1); // Сброс на первую страницу
            }}
          >
            <option value="hour">Последний час</option>
            <option value="shift">Последняя смена</option>
            <option value="day">Последний день</option>
            <option value="month">Последний месяц</option>
          </select>
        </div>

        <div className="filter-group">
          <label htmlFor="source">Источник:</label>
          <select
            id="source"
            value={eventSource}
            onChange={(e) => {
              setEventSource(e.target.value as EventSource);
              setPage(1); // Сброс на первую страницу
            }}
          >
            <option value="state">События по рейсу</option>
            <option value="tag">Теги по рейсу</option>
          </select>
        </div>
      </div>

      {/* Таблица событий */}
      {loading ? (
        <div className="loading">Загрузка...</div>
      ) : error ? (
        <div className="error-message">{error}</div>
      ) : events.length === 0 ? (
        <div className="no-events">
          <p>Нет событий за выбранный период</p>
        </div>
      ) : (
        <>
          <div className="events-table-container">
            <table className="events-table">
              <thead>
                <tr>
                  <th>Время</th>
                  <th>Тип события</th>
                  <th>Дополнительно</th>
                </tr>
              </thead>
              <tbody>
                {events.map((event) => (
                  <tr key={event.id}>
                    <td className="time-cell">{formatDateTime(event.timestamp)}</td>
                    <td className="event-type-cell">{getEventTypeText(event)}</td>
                    <td className="additional-cell">
                      <pre className="json-data">{getAdditionalInfo(event)}</pre>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Пагинация */}
          {pages > 1 && (
            <div className="pagination">
              <button
                className="pagination-button"
                onClick={() => setPage(page - 1)}
                disabled={page === 1}
              >
                ← Назад
              </button>
              <span className="pagination-info">
                Страница {page} из {pages} (всего событий: {total})
              </span>
              <button
                className="pagination-button"
                onClick={() => setPage(page + 1)}
                disabled={page === pages}
              >
                Вперёд →
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
};

