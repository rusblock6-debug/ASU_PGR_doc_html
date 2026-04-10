import { rtkApi } from '@/shared/api';
import type { PaginationFilter } from '@/shared/api/types';
import { getSearchParamsWithPagePagination, pageInfiniteQueryOptions } from '@/shared/api/utils';

import type { CreateRoleRequest, Role, RolesResponse, UpdateRoleRequest } from './types';

export const roleRtkApi = rtkApi.injectEndpoints({
  endpoints: (build) => ({
    getAllRoles: build.query<RolesResponse, void>({
      query: () => {
        return '/v1/roles';
      },

      providesTags: ['Roles'],
    }),

    getRoles: build.infiniteQuery<RolesResponse, void, PaginationFilter>({
      infiniteQueryOptions: pageInfiniteQueryOptions,

      query: ({ pageParam }) => {
        const params = getSearchParamsWithPagePagination(pageParam);

        return `/v1/roles?${params}`;
      },

      providesTags: ['Roles'],
    }),

    getRoleById: build.query<Role, number>({
      query(id) {
        return `/v1/roles/${id}`;
      },
    }),

    createRole: build.mutation<Role, CreateRoleRequest>({
      query: (body) => ({
        url: '/v1/roles',
        method: 'POST',
        body,
      }),

      invalidatesTags: ['Roles'],
    }),

    updateRole: build.mutation<Role, { id: number; body: UpdateRoleRequest }>({
      query: ({ id, body }) => ({
        url: `/v1/roles/${id}`,
        method: 'PUT',
        body: body,
      }),

      invalidatesTags: ['Roles'],
    }),

    deleteRole: build.mutation<void, number>({
      query: (id) => ({
        url: `/v1/roles/${id}`,
        method: 'DELETE',
      }),

      invalidatesTags: ['Roles'],
    }),
  }),
});

export const {
  useGetAllRolesQuery,
  useGetRolesInfiniteQuery,
  useGetRoleByIdQuery,
  useCreateRoleMutation,
  useUpdateRoleMutation,
  useDeleteRoleMutation,
} = roleRtkApi;
