import { rtkApi } from '@/shared/api';
import type { PaginationFilter } from '@/shared/api/types';
import { getSearchParamsWithPagePagination, pageInfiniteQueryOptions } from '@/shared/api/utils';

import type { CreateTagRequest, Tag, TagsApiResponse, UpdateTagParams } from './types';

export const tagsRtkApi = rtkApi.injectEndpoints({
  endpoints: (build) => ({
    getTags: build.infiniteQuery<TagsApiResponse, void, PaginationFilter>({
      infiniteQueryOptions: pageInfiniteQueryOptions,

      query: ({ pageParam }) => {
        const params = getSearchParamsWithPagePagination(pageParam);

        return `/tags?${params}`;
      },

      providesTags: ['Tag'],
    }),

    createTag: build.mutation<Tag, CreateTagRequest>({
      query: (body) => ({
        url: '/tags',
        method: 'POST',
        body,
      }),

      invalidatesTags: ['Tag'],
    }),

    updateTag: build.mutation<Tag, UpdateTagParams>({
      query: ({ id, body }) => ({
        url: `/tags/${id}`,
        method: 'PUT',
        body,
      }),

      invalidatesTags: ['Tag'],
    }),

    deleteTag: build.mutation<void, number>({
      query: (id) => ({
        url: `/tags/${id}`,
        method: 'DELETE',
      }),

      invalidatesTags: ['Tag'],
    }),
  }),
});

export const { useGetTagsInfiniteQuery, useCreateTagMutation, useUpdateTagMutation, useDeleteTagMutation } = tagsRtkApi;
