import type { PaginatedResponse } from '@/shared/api/endpoints/tasks/types';
import { rtkApi } from '@/shared/api/rtk-api';

import type { GetShiftTasksArgs, ShiftTaskChangedSsePayload, ShiftTaskResponse } from './types';

const SHIFT_TASKS_STREAM_PATH = '/api/events/stream/shift-tasks';
const INITIAL_RETRY_MS = 2_000;
const MAX_RETRY_MS = 30_000;

const shiftTasksApi = rtkApi.injectEndpoints({
  endpoints: (build) => ({
    getShiftTasks: build.query<PaginatedResponse<ShiftTaskResponse>, GetShiftTasksArgs | void>({
      query: (args) => {
        const params = new URLSearchParams();
        if (args?.page != null) {
          params.set('page', String(args.page));
        }
        if (args?.size != null) {
          params.set('size', String(args.size));
        }
        if (args?.shift_date) {
          params.set('shift_date', args.shift_date);
        }
        if (args?.vehicle_ids?.length) {
          for (const id of args.vehicle_ids) {
            params.append('vehicle_ids', String(id));
          }
        }
        if (args?.status_route_tasks?.length) {
          for (const s of args.status_route_tasks) {
            params.append('status_route_tasks', s);
          }
        }
        const qs = params.toString();
        return qs ? `/shift-tasks?${qs}` : '/shift-tasks';
      },
      providesTags: (result) =>
        result
          ? [
              ...result.items.map((item) => ({ type: 'ShiftTask' as const, id: item.id })),
              { type: 'ShiftTask', id: 'LIST' },
            ]
          : [{ type: 'ShiftTask', id: 'LIST' }],
    }),
    getShiftTaskById: build.query<ShiftTaskResponse, string>({
      query: (taskId) => `/shift-tasks/${taskId}`,
      providesTags: (_result, _error, id) => [{ type: 'ShiftTask', id }],
    }),

    /**
     * SSE-подписка на изменения наряд-заданий.
     * Инвалидирует теги ShiftTask / RouteTask при получении события.
     * При обрыве переподключается с exponential backoff.
     */
    subscribeShiftTasksStream: build.query<null, void>({
      queryFn: () => ({ data: null }),
      keepUnusedDataFor: 0,

      async onCacheEntryAdded(_, { cacheDataLoaded, cacheEntryRemoved, dispatch }) {
        await cacheDataLoaded;

        const base = import.meta.env.VITE_API_URL || '';
        const url = `${base}${SHIFT_TASKS_STREAM_PATH}`;

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

          source = new EventSource(url);

          source.addEventListener('open', () => {
            retryMs = INITIAL_RETRY_MS;
          });

          source.addEventListener('message', (event: MessageEvent<string>) => {
            try {
              const data = JSON.parse(event.data) as ShiftTaskChangedSsePayload;
              if (data.event_type === 'shift_task_changed' || data.shift_task_id) {
                dispatch(rtkApi.util.invalidateTags(['ShiftTask', 'RouteTask']));
              }
            } catch {
              dispatch(rtkApi.util.invalidateTags(['ShiftTask', 'RouteTask']));
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

export const {
  useGetShiftTasksQuery,
  useGetShiftTaskByIdQuery,
  useLazyGetShiftTaskByIdQuery,
  useSubscribeShiftTasksStreamQuery,
} = shiftTasksApi;
