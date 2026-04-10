import { rtkApi } from '@/shared/api/rtk-api';
import type { VehicleState, VehicleStreamEvent } from '@/shared/api/types/vehicle-events';
import { locationEventReceived, stateEventReceived, weightEventReceived } from '@/shared/lib/vehicle-events';

const INITIAL_RETRY_MS = 2_000;
const MAX_RETRY_MS = 30_000;

/**
 * Подписка на SSE-стрим событий борта `/api/events/stream/{vehicleId}`.
 * Обрабатывает state_event, location_event, weight_event; unknown_event игнорируется.
 * При обрыве соединения переподключается с exponential backoff.
 */
export const subscribeVehicleEventsSse = (dispatch: AppDispatch, vehicleId: string) => {
  const base = import.meta.env.VITE_API_URL || '';
  const url = `${base}/api/events/stream/${encodeURIComponent(vehicleId)}`;

  let source: EventSource | null = null;
  let retryMs = INITIAL_RETRY_MS;
  let retryTimer: ReturnType<typeof setTimeout> | null = null;
  let disposed = false;

  const handleMessage = (event: MessageEvent<string>) => {
    try {
      const data = JSON.parse(event.data) as VehicleStreamEvent;

      switch (data.event_type) {
        case 'state_event': {
          const raw = data as unknown as Record<string, unknown>;
          const status = (raw.status ?? raw.state) as VehicleState | undefined;
          const timestamp = (raw.timestamp as string) || new Date().toISOString();
          if (status) {
            dispatch(stateEventReceived({ event_type: 'state_event', status, timestamp }));
          }
          break;
        }
        case 'location_event':
          dispatch(locationEventReceived(data));
          break;
        case 'weight_event':
          dispatch(weightEventReceived(data));
          break;
        case 'assignments_alert':
          // Нам нужен только "create" по сообщению диспетчера.
          if (data.message_data?.message_event === 'create') {
            dispatch(rtkApi.util.invalidateTags(['ShiftTask', 'RouteTask']));
          }
          break;
        default:
          break;
      }
    } catch {
      // malformed JSON — пропускаем
    }
  };

  const connect = () => {
    if (disposed) return;

    source = new EventSource(url);

    source.addEventListener('open', () => {
      retryMs = INITIAL_RETRY_MS;
    });

    source.addEventListener('message', handleMessage);

    source.addEventListener('error', () => {
      source?.close();
      source = null;

      if (disposed) return;

      retryTimer = setTimeout(() => {
        retryMs = Math.min(retryMs * 2, MAX_RETRY_MS);
        connect();
      }, retryMs);
    });
  };

  connect();

  return () => {
    disposed = true;
    if (retryTimer != null) clearTimeout(retryTimer);
    source?.close();
    source = null;
  };
};
