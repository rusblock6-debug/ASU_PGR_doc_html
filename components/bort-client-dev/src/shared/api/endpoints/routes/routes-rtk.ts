import { rtkApi } from '@/shared/api/rtk-api';
import { VEHICLE_ID_NUM } from '@/shared/config/env';
import { parseRouteStreamPayload, routeProgressReceived, routeStreamUpdateReceived } from '@/shared/lib/route-stream';

import type {
  GetRouteBetweenNodesArgs,
  GetRouteProgressArgs,
  RouteBetweenNodesResponse,
  RouteProgressResponse,
} from './types';

const GRAPH_API_BASE = (import.meta.env.VITE_GRAPH_API_URL || '') + '/graph-api';
const ROUTES_STREAM_URL = `${GRAPH_API_BASE}/api/events/stream/routes`;
const INITIAL_RETRY_MS = 2_000;
const MAX_RETRY_MS = 30_000;

/** Событие SSE с процентом прогресса маршрута для текущего борта. */
interface RouteProgressEvent {
  event_type: 'route_progress';
  vehicle_id: number;
  progress_percent: number;
}

/** Runtime-проверка payload перед диспатчем routeProgressReceived. */
function isRouteProgressEvent(value: unknown): value is RouteProgressEvent {
  if (!value || typeof value !== 'object') return false;
  const obj = value as Record<string, unknown>;
  return (
    obj.event_type === 'route_progress' &&
    obj.vehicle_id === VEHICLE_ID_NUM &&
    typeof obj.progress_percent === 'number' &&
    Number.isFinite(obj.progress_percent)
  );
}

const routesApi = rtkApi.injectEndpoints({
  endpoints: (builder) => ({
    getRouteBetweenNodes: builder.query<RouteBetweenNodesResponse, GetRouteBetweenNodesArgs>({
      query: ({ startNodeId, targetNodeId }) =>
        `/api/route/${encodeURIComponent(String(startNodeId))}/${encodeURIComponent(String(targetNodeId))}`,
      extraOptions: { backend: 'graph' as const },
      providesTags: (_result, _error, { startNodeId, targetNodeId }) => [
        { type: 'Route' as const, id: `between:${startNodeId}:${targetNodeId}` },
      ],
    }),
    getRouteProgress: builder.query<RouteProgressResponse, GetRouteProgressArgs>({
      query: ({ startNodeId, targetNodeId, lat, lon }) => {
        const params = new URLSearchParams();
        params.set('lat', String(lat));
        params.set('lon', String(lon));
        return `/api/route/progress/${encodeURIComponent(String(startNodeId))}/${encodeURIComponent(String(targetNodeId))}?${params.toString()}`;
      },
      extraOptions: { backend: 'graph' as const },
      providesTags: (_result, _error, { startNodeId, targetNodeId }) => [
        { type: 'Route' as const, id: `progress:${startNodeId}:${targetNodeId}` },
      ],
    }),

    /**
     * SSE-поток метрик маршрута (дистанция, ETA) из Graph Service.
     * Данные диспатчатся в `routeStreamSlice` — потребители читают через селекторы.
     */
    getRoutesStream: builder.query<null, void>({
      queryFn: () => ({ data: null }),
      keepUnusedDataFor: 0,

      async onCacheEntryAdded(_, { cacheDataLoaded, cacheEntryRemoved, dispatch }) {
        await cacheDataLoaded;

        let source = null as EventSource | null;
        let retryMs = INITIAL_RETRY_MS;
        let retryTimer = null as ReturnType<typeof setTimeout> | null;
        let disposed = false;

        const scheduleRetry = () => {
          retryTimer = setTimeout(connect, retryMs);
          retryMs = Math.min(retryMs * 2, MAX_RETRY_MS);
        };

        const connect = () => {
          if (disposed) return;

          source = new EventSource(ROUTES_STREAM_URL);

          source.addEventListener('open', () => {
            retryMs = INITIAL_RETRY_MS;
          });

          source.addEventListener('message', (event: MessageEvent<string>) => {
            try {
              const data: unknown = JSON.parse(event.data);
              const metrics = parseRouteStreamPayload(data);
              dispatch(routeStreamUpdateReceived(metrics));

              const items = Array.isArray(data) ? data : [data];
              for (const item of items) {
                if (isRouteProgressEvent(item)) {
                  dispatch(routeProgressReceived(item.progress_percent));
                  break;
                }
              }
            } catch {
              // malformed JSON — пропускаем
            }
          });

          source.addEventListener('error', () => {
            source?.close();
            source = null;
            if (disposed) return;
            scheduleRetry();
          });
        };

        connect();

        await cacheEntryRemoved;
        disposed = true;
        if (retryTimer != null) clearTimeout(retryTimer);
        if (source) source.close();
      },
    }),
  }),
});

export const { useGetRouteBetweenNodesQuery, useGetRouteProgressQuery, useGetRoutesStreamQuery } = routesApi;
