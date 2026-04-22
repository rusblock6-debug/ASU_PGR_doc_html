import { rtkApi } from '@/shared/api';
import type { PaginationFilter } from '@/shared/api/types';
import { getSearchParamsWithPagePagination, pageInfiniteQueryOptions } from '@/shared/api/utils';

import type {
  CreateSubstratePayload,
  RefreshSubstrateFilePayload,
  SubstrateListResponse,
  SubstrateResponse,
  SubstrateUpdate,
  SubstrateWithSvgResponse,
} from './types';

export const substratesRtkApi = rtkApi.injectEndpoints({
  endpoints: (build) => ({
    getSubstrates: build.infiniteQuery<SubstrateListResponse, void, PaginationFilter>({
      infiniteQueryOptions: pageInfiniteQueryOptions,
      query: ({ pageParam }) => {
        const params = getSearchParamsWithPagePagination(pageParam);

        return `/graph/substrates?${params.toString()}`;
      },
      providesTags: ['Substrates'],
    }),

    getSubstrateById: build.query<SubstrateWithSvgResponse, number>({
      query: (id) => `/graph/substrates/${id}`,
      providesTags: ['Substrates'],
    }),

    createSubstrate: build.mutation<SubstrateResponse, CreateSubstratePayload>({
      query: ({ file, horizon_id: horizonId, opacity, center }) => {
        const formData = new FormData();

        formData.append('file', file);

        if (horizonId !== undefined) {
          if (horizonId === null) {
            formData.append('horizon_id', '');
          } else {
            formData.append('horizon_id', String(horizonId));
          }
        }

        if (opacity !== undefined) {
          formData.append('opacity', String(opacity));
        }

        if (center !== undefined) {
          formData.append('center', JSON.stringify(center));
        }

        return {
          url: '/graph/substrates',
          method: 'POST',
          body: formData,
        };
      },
      invalidatesTags: ['Substrates'],
    }),

    updateSubstrate: build.mutation<SubstrateResponse, { id: number; body: SubstrateUpdate }>({
      query: ({ id, body }) => ({
        url: `/graph/substrates/${id}`,
        method: 'PATCH',
        body,
      }),
      invalidatesTags: ['Substrates'],
    }),

    deleteSubstrate: build.mutation<void, number>({
      query: (id) => ({
        url: `/graph/substrates/${id}`,
        method: 'DELETE',
      }),
      invalidatesTags: ['Substrates'],
    }),

    refreshSubstrateFile: build.mutation<SubstrateResponse, RefreshSubstrateFilePayload>({
      query: ({ id, file }) => {
        const formData = new FormData();

        formData.append('file', file);

        return {
          url: `/graph/substrates/${id}/refresh_file`,
          method: 'POST',
          body: formData,
        };
      },
      invalidatesTags: ['Substrates'],
    }),
  }),
});

export const {
  useGetSubstratesInfiniteQuery,
  useGetSubstrateByIdQuery,
  useCreateSubstrateMutation,
  useUpdateSubstrateMutation,
  useDeleteSubstrateMutation,
  useRefreshSubstrateFileMutation,
} = substratesRtkApi;
