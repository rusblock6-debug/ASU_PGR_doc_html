import { rtkApi } from '@/shared/api/rtk-api';
import type { PaginatedResponse, ShiftTaskResponse, TripStatusRouteEnum } from '@/shared/api/types/trip-service';

/**
 * Параметры запроса списка сменных заданий.
 */
export interface GetShiftTasksArgs {
  readonly page?: number;
  readonly size?: number;
  readonly shift_date?: string;
  readonly vehicle_ids?: number[];
  readonly status_route_tasks?: TripStatusRouteEnum[];
}

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
  }),
});

export const { useGetShiftTasksQuery, useGetShiftTaskByIdQuery, useLazyGetShiftTaskByIdQuery } = shiftTasksApi;
