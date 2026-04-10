import { rtkApi } from '@/shared/api/rtk-api';
import type {
  ActiveTaskResponse,
  PaginatedResponse,
  RouteTaskResponse,
  RouteTaskUpdateBody,
  TripStatusRouteEnum,
} from '@/shared/api/types/trip-service';
import { VEHICLE_ID_STR } from '@/shared/config/env';

/**
 * Параметры запроса списка маршрутных заданий.
 */
export interface GetRouteTasksArgs {
  readonly page?: number;
  readonly size?: number;
  readonly shift_task_id?: string | null;
  readonly task_status?: TripStatusRouteEnum | null;
}

const tasksApi = rtkApi.injectEndpoints({
  endpoints: (build) => ({
    getRouteTasks: build.query<PaginatedResponse<RouteTaskResponse>, GetRouteTasksArgs | void>({
      query: (args) => {
        const params = new URLSearchParams();
        if (args?.page != null) {
          params.set('page', String(args.page));
        }
        if (args?.size != null) {
          params.set('size', String(args.size));
        }
        if (args?.shift_task_id) {
          params.set('shift_task_id', args.shift_task_id);
        }
        if (args?.task_status) {
          params.set('task_status', args.task_status);
        }
        const qs = params.toString();
        return qs ? `/tasks?${qs}` : '/tasks';
      },
      providesTags: (result) =>
        result
          ? [
              ...result.items.map((item) => ({ type: 'RouteTask' as const, id: item.id })),
              { type: 'RouteTask', id: 'LIST' },
            ]
          : [{ type: 'RouteTask', id: 'LIST' }],
    }),
    getRouteTaskById: build.query<RouteTaskResponse, string>({
      query: (id) => `/tasks/${id}`,
      providesTags: (_result, _error, id) => [{ type: 'RouteTask', id }],
    }),
    getActiveTask: build.query<ActiveTaskResponse, void>({
      query: () => '/active/task',
      providesTags: [{ type: 'ActiveTask', id: 'CURRENT' }],
    }),
    activateRouteTask: build.mutation<RouteTaskResponse, { taskId: string; vehicleId?: string }>({
      query: ({ taskId, vehicleId = VEHICLE_ID_STR }) => ({
        url: `/tasks/${taskId}/activate?vehicle_id=${encodeURIComponent(vehicleId)}`,
        method: 'PUT',
      }),
      invalidatesTags: (_result, _error, { taskId }) => [
        { type: 'RouteTask', id: taskId },
        { type: 'RouteTask', id: 'LIST' },
        { type: 'ShiftTask', id: 'LIST' },
        { type: 'ActiveTask', id: 'CURRENT' },
      ],
    }),
    cancelRouteTask: build.mutation<RouteTaskResponse, { taskId: string; vehicleId?: string }>({
      query: ({ taskId, vehicleId = VEHICLE_ID_STR }) => ({
        url: `/tasks/${taskId}/cancel?vehicle_id=${encodeURIComponent(vehicleId)}`,
        method: 'PUT',
      }),
      invalidatesTags: (_result, _error, { taskId }) => [
        { type: 'RouteTask', id: taskId },
        { type: 'RouteTask', id: 'LIST' },
        { type: 'ShiftTask', id: 'LIST' },
        { type: 'ActiveTask', id: 'CURRENT' },
      ],
    }),
    updateRouteTask: build.mutation<RouteTaskResponse, { taskId: string; body: RouteTaskUpdateBody }>({
      query: ({ taskId, body }) => ({
        url: `/tasks/${taskId}`,
        method: 'PUT',
        body,
      }),
      invalidatesTags: (_result, _error, { taskId }) => [
        { type: 'RouteTask', id: taskId },
        { type: 'RouteTask', id: 'LIST' },
        { type: 'ShiftTask', id: 'LIST' },
        { type: 'ActiveTask', id: 'CURRENT' },
      ],
    }),
    completeActiveTrip: build.mutation<unknown, void>({
      query: () => ({
        url: '/active/trip/complete',
        method: 'PUT',
      }),
      invalidatesTags: [
        { type: 'RouteTask', id: 'LIST' },
        { type: 'ShiftTask', id: 'LIST' },
        { type: 'ActiveTask', id: 'CURRENT' },
      ],
    }),
    clearActiveTask: build.mutation<unknown, void>({
      query: () => ({
        url: '/active/task',
        method: 'DELETE',
      }),
      invalidatesTags: [
        { type: 'RouteTask', id: 'LIST' },
        { type: 'ShiftTask', id: 'LIST' },
        { type: 'ActiveTask', id: 'CURRENT' },
      ],
    }),
  }),
});

export const {
  useGetRouteTasksQuery,
  useGetRouteTaskByIdQuery,
  useGetActiveTaskQuery,
  useActivateRouteTaskMutation,
  useCancelRouteTaskMutation,
  useUpdateRouteTaskMutation,
  useCompleteActiveTripMutation,
  useClearActiveTaskMutation,
} = tasksApi;
