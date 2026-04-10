import { rtkApi } from '@/shared/api';
import type { PaginationFilter } from '@/shared/api/types';
import { getSearchParamsWithPagePagination, pageInfiniteQueryOptions } from '@/shared/api/utils';

import type {
  CreateLoadTypeRequest,
  LoadType,
  LoadTypesApiResponse,
  NormalizedLoadTypes,
  UpdateLoadTypeParams,
} from './types';

export const loadTypesRtkApi = rtkApi.injectEndpoints({
  endpoints: (build) => ({
    getAllLoadType: build.query<NormalizedLoadTypes, void>({
      query: () => '/load_types',

      transformResponse: (response: LoadTypesApiResponse): NormalizedLoadTypes => {
        const ids: number[] = [];
        const entities: Record<number, LoadType> = {};
        for (const item of response.items) {
          ids.push(item.id);
          entities[item.id] = item;
        }
        return { ids, entities };
      },

      providesTags: ['Load-types'],
    }),

    getLoadTypes: build.infiniteQuery<LoadTypesApiResponse, void, PaginationFilter>({
      infiniteQueryOptions: pageInfiniteQueryOptions,

      query: ({ pageParam }) => {
        const params = getSearchParamsWithPagePagination(pageParam);

        return `/load_types?${params}`;
      },

      providesTags: ['Load-types'],
    }),

    createLoadType: build.mutation<LoadType, CreateLoadTypeRequest>({
      query: (body) => ({
        url: '/load_types',
        method: 'POST',
        body,
      }),

      invalidatesTags: ['Load-types'],
    }),

    updateLoadType: build.mutation<LoadType, UpdateLoadTypeParams>({
      query: ({ id, body }) => ({
        url: `/load_types/${id}`,
        method: 'PUT',
        body,
      }),

      invalidatesTags: ['Load-types'],
    }),

    deleteLoadType: build.mutation<void, number>({
      query: (id) => ({
        url: `/load_types/${id}`,
        method: 'DELETE',
      }),

      invalidatesTags: ['Load-types'],
    }),
  }),
});

export const {
  useGetAllLoadTypeQuery,
  useGetLoadTypesInfiniteQuery,
  useCreateLoadTypeMutation,
  useUpdateLoadTypeMutation,
  useDeleteLoadTypeMutation,
} = loadTypesRtkApi;
