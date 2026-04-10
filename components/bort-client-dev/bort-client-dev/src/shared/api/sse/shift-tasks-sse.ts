import { rtkApi } from '@/shared/api/rtk-api';
import type { ShiftTaskChangedSsePayload } from '@/shared/api/types/trip-service';

const SHIFT_TASKS_STREAM_PATH = '/api/events/stream/shift-tasks';

const INITIAL_RETRY_MS = 2_000;
const MAX_RETRY_MS = 30_000;

/**
 * Опции подписки на SSE наряд-заданий.
 */
export interface SubscribeShiftTasksSseOptions {
  /** Вызывается для каждого успешно распарсенного события (до инвалидации тегов). */
  readonly onPayload?: (payload: ShiftTaskChangedSsePayload) => void;
}

/**
 * Подписка на SSE обновления наряд-заданий; инвалидирует теги RTK Query.
 * При обрыве соединения переподключается с exponential backoff.
 */
export const subscribeShiftTasksSse = (dispatch: AppDispatch, options?: SubscribeShiftTasksSseOptions) => {
  const base = import.meta.env.VITE_API_URL || '';
  const url = `${base}${SHIFT_TASKS_STREAM_PATH}`;

  let source: EventSource | null = null;
  let retryMs = INITIAL_RETRY_MS;
  let retryTimer: ReturnType<typeof setTimeout> | null = null;
  let disposed = false;

  const handleMessage = (event: MessageEvent<string>) => {
    try {
      const data = JSON.parse(event.data) as ShiftTaskChangedSsePayload;
      options?.onPayload?.(data);
      if (data.event_type === 'shift_task_changed' || data.shift_task_id) {
        dispatch(rtkApi.util.invalidateTags(['ShiftTask', 'RouteTask']));
      }
    } catch {
      dispatch(rtkApi.util.invalidateTags(['ShiftTask', 'RouteTask']));
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
