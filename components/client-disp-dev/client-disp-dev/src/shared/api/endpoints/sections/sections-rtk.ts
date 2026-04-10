import { rtkApi } from '@/shared/api';
import type { PaginationFilter } from '@/shared/api/types';
import { getSearchParamsWithPagePagination, pageInfiniteQueryOptions } from '@/shared/api/utils';

import type { CreateSectionRequest, Section, SectionsResponse, UpdateSectionRequest } from './types';

export const sectionsRtkApi = rtkApi.injectEndpoints({
  endpoints: (builder) => ({
    getAllSections: builder.query<SectionsResponse, void>({
      query() {
        return '/sections';
      },

      providesTags: ['Sections'],
    }),

    getSections: builder.infiniteQuery<SectionsResponse, void, PaginationFilter>({
      infiniteQueryOptions: pageInfiniteQueryOptions,

      query: ({ pageParam }) => {
        const params = getSearchParamsWithPagePagination(pageParam);

        return `/sections?${params}`;
      },

      providesTags: ['Sections'],
    }),

    createSection: builder.mutation<Section, CreateSectionRequest>({
      query: (body) => ({
        url: '/sections',
        method: 'POST',
        body,
      }),

      invalidatesTags: ['Sections'],
    }),

    updateSection: builder.mutation<Section, { sectionId: number; body: UpdateSectionRequest }>({
      query: ({ sectionId, body }) => ({
        url: `/sections/${sectionId}`,
        method: 'PATCH',
        body,
      }),

      invalidatesTags: ['Sections'],
    }),

    deleteSection: builder.mutation<void, number>({
      query: (sectionId) => ({
        url: `/sections/${sectionId}`,
        method: 'DELETE',
      }),

      invalidatesTags: ['Sections'],
    }),
  }),
});

export const {
  useGetAllSectionsQuery,
  useGetSectionsInfiniteQuery,
  useCreateSectionMutation,
  useUpdateSectionMutation,
  useDeleteSectionMutation,
} = sectionsRtkApi;
