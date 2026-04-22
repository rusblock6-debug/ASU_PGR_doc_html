import { rtkApi } from '@/shared/api';
import { hasValue } from '@/shared/lib/has-value';

import type {
  ActivateRouteTaskRequest,
  CancelRouteTaskRequest,
  RouteTask,
  RouteTaskBulkUpsertRequest,
  RouteTaskBulkUpsertResponse,
  RouteTasksQueryArgs,
  RouteTasksResponse,
  RouteTaskUpsertItem,
} from './types';

export const routeTasksRtkApi = rtkApi.injectEndpoints({
  endpoints: (build) => ({
    getAllTasks: build.query<RouteTasksResponse, RouteTasksQueryArgs | void>({
      query(queryArg) {
        const params = new URLSearchParams();

        if (hasValue(queryArg?.task_status)) {
          params.append('task_status', queryArg.task_status);
        }
        if (hasValue(queryArg?.shift_task_id)) {
          params.append('shift_task_id', queryArg.shift_task_id);
        }
        if (hasValue(queryArg?.vehicle_id)) {
          params.append('vehicle_id', String(queryArg.vehicle_id));
        }
        if (hasValue(queryArg?.place_a_id)) {
          params.append('place_a_id', String(queryArg.place_a_id));
        }
        if (hasValue(queryArg?.place_b_id)) {
          params.append('place_b_id', String(queryArg.place_b_id));
        }

        const query = params.toString();
        return query ? `/trip/tasks?${query}` : '/trip/tasks';
      },

      providesTags: ['Shift-tasks'],
    }),

    getTaskById: build.query<RouteTask, string>({
      query: (id) => ({
        url: `/trip/tasks/${id}`,
      }),
    }),

    createRouteTask: build.mutation<RouteTask, RouteTaskUpsertItem>({
      query: (body) => ({
        url: '/trip/tasks',
        method: 'POST',
        body,
      }),
      invalidatesTags: ['Shift-tasks'],
    }),

    updateRouteTask: build.mutation<RouteTask, { readonly id: string; readonly body: RouteTaskUpsertItem }>({
      query: ({ id, body }) => ({
        url: `/trip/tasks/${id}`,
        method: 'PUT',
        body,
      }),
      invalidatesTags: ['Shift-tasks'],
    }),

    upsertRouteTasks: build.mutation<RouteTaskBulkUpsertResponse, RouteTaskBulkUpsertRequest>({
      query: (body) => ({
        url: '/trip/tasks/upsert-bulk',
        method: 'POST',
        body,
      }),
      // Инвалидируем кеш shift-tasks, так как route-tasks являются частью shift-tasks.
      invalidatesTags: ['Shift-tasks'],
    }),

    activateRouteTask: build.mutation<RouteTask, ActivateRouteTaskRequest>({
      query: ({ taskId, vehicleId }) => ({
        url: `/trip/tasks/${taskId}/activate`,
        method: 'PUT',
        params: { vehicle_id: vehicleId },
      }),

      invalidatesTags: ['Shift-tasks'],
    }),

    cancelRouteTask: build.mutation<RouteTask, CancelRouteTaskRequest>({
      query: ({ taskId, vehicleId }) => ({
        url: `/trip/tasks/${taskId}/cancel`,
        method: 'PUT',
        params: { vehicle_id: vehicleId },
      }),

      invalidatesTags: ['Shift-tasks'],
    }),
  }),
});

export const {
  useGetAllTasksQuery,
  useGetTaskByIdQuery,
  useUpsertRouteTasksMutation,
  useActivateRouteTaskMutation,
  useCancelRouteTaskMutation,
  useCreateRouteTaskMutation,
  useUpdateRouteTaskMutation,
} = routeTasksRtkApi;
