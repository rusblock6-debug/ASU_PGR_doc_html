import { rtkApi } from '@/shared/api';
import type { PaginationFilter } from '@/shared/api/types';
import { getSearchParamsWithPagePagination, pageInfiniteQueryOptions } from '@/shared/api/utils';

import type {
  PreviewFromPreviousShiftRequest,
  ShiftTask,
  ShiftTaskBulkUpsertRequest,
  ShiftTaskBulkUpsertResponse,
  ShiftTasksQueryArg,
  ShiftTasksResponse,
  ShiftTaskStreamMessage,
} from './types';

const MAX_PAGE_SIZE = 100;

export const shiftTaskRtkApi = rtkApi.injectEndpoints({
  endpoints: (build) => ({
    getShiftTasks: build.infiniteQuery<ShiftTasksResponse, ShiftTasksQueryArg, PaginationFilter>({
      infiniteQueryOptions: pageInfiniteQueryOptions,

      query({ queryArg, pageParam }) {
        const params = getSearchParamsWithPagePagination(pageParam);

        if (queryArg.status) {
          params.append('status', queryArg.status);
        }
        if (queryArg.shift_date) {
          params.append('shift_date', queryArg.shift_date);
        }
        if (queryArg.vehicle_ids) {
          queryArg.vehicle_ids.forEach((id) => params.append('vehicle_ids', String(id)));
        }
        if (queryArg.shift_num) {
          params.append('shift_num', String(queryArg.shift_num));
        }
        if (queryArg.status_route_tasks) {
          queryArg.status_route_tasks.forEach((status) => params.append('status_route_tasks', status));
        }

        return `/shift-tasks?${params}`;
      },

      providesTags: ['Shift-tasks'],

      keepUnusedDataFor: 0,
    }),

    /**
     * Получить все наряд-задания для указанных машин. По умолчанию используйте `getShiftTasks`.
     *
     * Используется перед отправкой на сервер при активном фильтре по статусу (`selectedStatus !== 'all'`).
     * Основной кеш `getShiftTasks` содержит только отфильтрованные `route_tasks`, а API `bulk-upsert` заменяет
     * весь список `route_tasks` целиком — задачи, не включённые в payload, удаляются на сервере.
     *
     * Запрашиваем данные без `status_route_tasks`, чтобы `buildApiItems` сформировал корректный набор данных со всеми `route_tasks`.
     *
     * API ограничивает параметр `size` до 100 элементов на страницу, поэтому `vehicle_ids` разбиваются на чанки и запрашиваются параллельно.
     */
    getShiftTasksList: build.query<ShiftTasksResponse, ShiftTasksQueryArg>({
      async queryFn(queryArg, _queryApi, _extraOptions, baseQuery) {
        const vehicleIds = queryArg.vehicle_ids ?? [];

        const buildParams = (chunk: readonly number[]) => {
          const params = getSearchParamsWithPagePagination({ size: chunk.length });
          if (queryArg.shift_date) params.append('shift_date', queryArg.shift_date);
          if (queryArg.shift_num) params.append('shift_num', String(queryArg.shift_num));
          chunk.forEach((id) => params.append('vehicle_ids', String(id)));
          return params;
        };

        const chunks: number[][] = [];
        for (let i = 0; i < vehicleIds.length; i += MAX_PAGE_SIZE) {
          chunks.push(vehicleIds.slice(i, i + MAX_PAGE_SIZE));
        }

        if (chunks.length === 0) {
          return { data: { items: [], total: 0, page: 1, size: 0, pages: 1 } };
        }

        const results = await Promise.all(
          chunks.map((chunk) => Promise.resolve(baseQuery(`/shift-tasks?${buildParams(chunk)}`))),
        );

        const firstError = results.find((item) => item.error);
        if (firstError?.error) {
          return { error: firstError.error };
        }

        const allItems = results.flatMap((item) => (item.data as ShiftTasksResponse).items);

        return {
          data: { items: allItems, total: allItems.length, page: 1, size: allItems.length, pages: 1 },
        };
      },
      keepUnusedDataFor: 0,
    }),

    upsertShiftTasks: build.mutation<ShiftTaskBulkUpsertResponse, ShiftTaskBulkUpsertRequest>({
      query: (body) => ({
        url: '/shift-tasks/bulk-upsert',
        method: 'POST',
        body,
      }),
      invalidatesTags: ['Shift-tasks'],
    }),

    previewFromPreviousShift: build.query<ShiftTask[], PreviewFromPreviousShiftRequest>({
      query: (params) => ({
        url: '/shift-tasks/preview-from-previous',
        method: 'POST',
        params,
      }),
    }),

    /**
     * SSE-поток событий наряд-заданий.
     * Кеш хранит массив событий — это гарантирует, что при быстром поступлении нескольких SSE-событий
     * ни одно не будет потеряно из-за батчинга React рендера.
     */
    getShiftTasksStream: build.query<ShiftTaskStreamMessage[], void>({
      queryFn: () => ({ data: [] }),
      keepUnusedDataFor: 0,

      async onCacheEntryAdded(_, { updateCachedData, cacheDataLoaded, cacheEntryRemoved }) {
        const eventSource = new EventSource('/api/events/stream/shift-tasks');

        try {
          await cacheDataLoaded;

          eventSource.onmessage = (event: MessageEvent<string>) => {
            const data = JSON.parse(event.data) as ShiftTaskStreamMessage;

            updateCachedData((draft) => [...draft, data]);
          };

          await cacheEntryRemoved;
        } finally {
          eventSource.close();
        }
      },
    }),
  }),
});

export const {
  useGetShiftTasksInfiniteQuery,
  useUpsertShiftTasksMutation,
  useLazyPreviewFromPreviousShiftQuery,
  useLazyGetShiftTasksListQuery,
  useGetShiftTasksStreamQuery,
} = shiftTaskRtkApi;
