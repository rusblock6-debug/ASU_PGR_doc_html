import { rtkApi } from '@/shared/api';
import type { PaginationFilter } from '@/shared/api/types';
import { getSearchParamsWithPagePagination, pageInfiniteQueryOptions } from '@/shared/api/utils';

import type {
  CreateHorizonRequest,
  Horizon,
  HorizonGraphResponse,
  HorizonResponse,
  UpdateHorizonGraphRequest,
  UpdateHorizonRequest,
} from './types';

export const horizonsRtkApi = rtkApi.injectEndpoints({
  endpoints: (builder) => ({
    getAllHorizons: builder.query<HorizonResponse, void>({
      query: () => {
        return `/graph/horizons`;
      },

      providesTags: ['Horizons'],
    }),

    getHorizons: builder.infiniteQuery<HorizonResponse, void, PaginationFilter>({
      infiniteQueryOptions: pageInfiniteQueryOptions,

      query: ({ pageParam }) => {
        const params = getSearchParamsWithPagePagination(pageParam);

        return `/graph/horizons?${params}`;
      },

      providesTags: ['Horizons'],
    }),

    createHorizon: builder.mutation<Horizon, CreateHorizonRequest>({
      query: (body) => ({
        url: '/graph/horizons',
        method: 'POST',
        body,
      }),

      invalidatesTags: ['Horizons'],
    }),

    updateHorizon: builder.mutation<Horizon, { horizonId: number; body: UpdateHorizonRequest }>({
      query: ({ horizonId, body }) => ({
        url: `/graph/horizons/${horizonId}`,
        method: 'PATCH',
        body,
      }),

      invalidatesTags: ['Horizons'],
    }),

    deleteHorizon: builder.mutation<void, number>({
      query: (horizonId) => ({
        url: `/graph/horizons/${horizonId}`,
        method: 'DELETE',
      }),

      invalidatesTags: ['Horizons'],
    }),

    getHorizonGraph: builder.query<HorizonGraphResponse, number>({
      query: (horizonId) => `/graph/horizons/${horizonId}/graph`,

      providesTags: ['Horizons'],
    }),

    updateHorizonGraph: builder.mutation<unknown, { horizonId: number; body: UpdateHorizonGraphRequest }>({
      query: ({ horizonId, body }) => ({
        url: `/graph/horizons/${horizonId}/graph/bulk-upsert`,
        method: 'POST',
        body,
      }),

      invalidatesTags: ['Horizons'],
    }),
  }),
});

export const {
  useGetAllHorizonsQuery,
  useGetHorizonsInfiniteQuery,
  useGetHorizonGraphQuery,
  useLazyGetHorizonGraphQuery,
  useCreateHorizonMutation,
  useUpdateHorizonMutation,
  useUpdateHorizonGraphMutation,
  useDeleteHorizonMutation,
} = horizonsRtkApi;
