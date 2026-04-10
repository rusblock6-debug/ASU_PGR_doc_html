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

        return `/substrates?${params.toString()}`;
      },
      providesTags: ['Substrates'],
    }),

    getSubstrateById: build.query<SubstrateWithSvgResponse, number>({
      query: (id) => `/substrates/${id}`,
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
          url: '/substrates',
          method: 'POST',
          body: formData,
        };
      },
      invalidatesTags: ['Substrates'],
    }),

    updateSubstrate: build.mutation<SubstrateResponse, { id: number; body: SubstrateUpdate }>({
      query: ({ id, body }) => ({
        url: `/substrates/${id}`,
        method: 'PATCH',
        body,
      }),
      invalidatesTags: ['Substrates'],
    }),

    deleteSubstrate: build.mutation<void, number>({
      query: (id) => ({
        url: `/substrates/${id}`,
        method: 'DELETE',
      }),
      invalidatesTags: ['Substrates'],
    }),

    refreshSubstrateFile: build.mutation<SubstrateResponse, RefreshSubstrateFilePayload>({
      query: ({ id, file }) => {
        const formData = new FormData();

        formData.append('file', file);

        return {
          url: `/substrates/${id}/refresh_file`,
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
