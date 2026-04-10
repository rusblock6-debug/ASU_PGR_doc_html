import { parseRouteStreamPayload, routeStreamUpdateReceived } from '@/shared/lib/route-stream';

/** Как в `graph-api.ts`: пустой `VITE_GRAPH_API_URL` → `/graph-api` (Vite proxy на Graph Service :5001). */
const GRAPH_API_BASE = (import.meta.env.VITE_GRAPH_API_URL || '') + '/graph-api';
const ROUTES_STREAM_PATH = '/api/events/stream/routes';

const INITIAL_RETRY_MS = 2_000;
const MAX_RETRY_MS = 30_000;

/**
 * SSE Graph Service `/api/events/stream/routes`: метры и минуты до точки назначения.
 * Формат JSON — см. parseRouteStreamPayload; при смене контракта обновить парсер.
 */
export const subscribeRoutesStreamSse = (dispatch: AppDispatch) => {
  const url = `${GRAPH_API_BASE}${ROUTES_STREAM_PATH}`;

  let source: EventSource | null = null;
  let retryMs = INITIAL_RETRY_MS;
  let retryTimer: ReturnType<typeof setTimeout> | null = null;
  let disposed = false;

  const handleMessage = (event: MessageEvent<string>) => {
    try {
      const data: unknown = JSON.parse(event.data);
      const metrics = parseRouteStreamPayload(data);
      dispatch(routeStreamUpdateReceived(metrics));
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
