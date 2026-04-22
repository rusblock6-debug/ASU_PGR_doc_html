import { rtkApi } from '@/shared/api';
import type { PaginationFilter } from '@/shared/api/types';
import { getSearchParamsWithPagePagination, pageInfiniteQueryOptions } from '@/shared/api/utils';

import type { CreateStatusRequest, Status, StatusResponse, UpdateStatusRequest } from './types';

export const statusesRtkApi = rtkApi.injectEndpoints({
  endpoints: (builder) => ({
    getAllStatuses: builder.query<StatusResponse, void>({
      query: () => {
        return `/enterprise/statuses`;
      },

      providesTags: ['Statuses'],
    }),

    getStatuses: builder.infiniteQuery<StatusResponse, void, PaginationFilter>({
      infiniteQueryOptions: pageInfiniteQueryOptions,

      query: ({ pageParam }) => {
        const params = getSearchParamsWithPagePagination(pageParam);

        return `/enterprise/statuses?${params}`;
      },

      providesTags: ['Statuses'],
    }),

    createStatus: builder.mutation<Status, CreateStatusRequest>({
      query: (body) => ({
        url: '/enterprise/statuses',
        method: 'POST',
        body,
      }),

      invalidatesTags: ['Statuses'],
    }),

    updateStatus: builder.mutation<Status, { statusId: number; body: UpdateStatusRequest }>({
      query: ({ statusId, body }) => ({
        url: `/enterprise/statuses/${statusId}`,
        method: 'PUT',
        body,
      }),

      invalidatesTags: ['Statuses'],
    }),

    deleteStatus: builder.mutation<void, number>({
      query: (statusId) => ({
        url: `/enterprise/statuses/${statusId}`,
        method: 'DELETE',
      }),

      invalidatesTags: ['Statuses'],
    }),
  }),
});

export const {
  useGetAllStatusesQuery,
  useGetStatusesInfiniteQuery,
  useCreateStatusMutation,
  useUpdateStatusMutation,
  useDeleteStatusMutation,
} = statusesRtkApi;
