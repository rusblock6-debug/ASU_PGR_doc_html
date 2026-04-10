import { rtkApi } from '@/shared/api';

import type {
  CreateLoadTypeCategoryRequest,
  LoadTypeCategoriesApiResponse,
  LoadTypeCategory,
  UpdateLoadTypeCategoryParams,
} from './types';

export const loadTypeCategoriesRtkApi = rtkApi.injectEndpoints({
  endpoints: (build) => ({
    getAllLoadTypeCategories: build.query<readonly LoadTypeCategory[], void>({
      query: () => '/load_type_categories',

      transformResponse: (response: LoadTypeCategoriesApiResponse) => response.items,

      providesTags: ['Load-type-categories'],
    }),

    createLoadTypeCategory: build.mutation<LoadTypeCategory, CreateLoadTypeCategoryRequest>({
      query: (body) => ({
        url: '/load_type_categories',
        method: 'POST',
        body,
      }),
      invalidatesTags: ['Load-type-categories'],
    }),

    updateLoadTypeCategory: build.mutation<LoadTypeCategory, UpdateLoadTypeCategoryParams>({
      query: ({ id, body }) => ({
        url: `/load_type_categories/${id}`,
        method: 'PUT',
        body,
      }),
      invalidatesTags: ['Load-type-categories'],
    }),

    deleteLoadTypeCategory: build.mutation<void, number>({
      query: (id) => ({
        url: `/load_type_categories/${id}`,
        method: 'DELETE',
      }),
      invalidatesTags: ['Load-type-categories'],
    }),
  }),
});

export const {
  useGetAllLoadTypeCategoriesQuery,
  useCreateLoadTypeCategoryMutation,
  useUpdateLoadTypeCategoryMutation,
  useDeleteLoadTypeCategoryMutation,
} = loadTypeCategoriesRtkApi;
