import { rtkApi } from '@/shared/api';

import type {
  CreateOrganizationCategoryRequest,
  OrganizationCategory,
  OrganizationCategoryResponse,
  UpdateOrganizationCategoryRequest,
} from './types';

export const organizationCategoriesRtkApi = rtkApi.injectEndpoints({
  endpoints: (builder) => ({
    getAllOrganizationCategories: builder.query<OrganizationCategoryResponse, void>({
      query: () => {
        return '/enterprise/organization-categories';
      },

      providesTags: ['Organization-categories'],
    }),

    createOrganizationCategory: builder.mutation<OrganizationCategory, CreateOrganizationCategoryRequest>({
      query: (body) => ({
        url: '/enterprise/organization-categories',
        method: 'POST',
        body,
      }),

      invalidatesTags: ['Organization-categories'],
    }),

    updateOrganizationCategory: builder.mutation<
      OrganizationCategory,
      { organizationCategoryId: number; body: UpdateOrganizationCategoryRequest }
    >({
      query: ({ organizationCategoryId, body }) => ({
        url: `/enterprise/organization-categories/${organizationCategoryId}`,
        method: 'PUT',
        body,
      }),

      invalidatesTags: ['Organization-categories'],
    }),

    deleteOrganizationCategory: builder.mutation<void, number>({
      query: (organizationCategoryId) => ({
        url: `/enterprise/organization-categories/${organizationCategoryId}`,
        method: 'DELETE',
      }),

      invalidatesTags: ['Organization-categories'],
    }),
  }),
});

export const {
  useGetAllOrganizationCategoriesQuery,
  useCreateOrganizationCategoryMutation,
  useUpdateOrganizationCategoryMutation,
  useDeleteOrganizationCategoryMutation,
} = organizationCategoriesRtkApi;
