import { rtkApi } from '@/shared/api';
import type { PaginationFilter } from '@/shared/api/types';
import { getSearchParamsWithPagePagination, pageInfiniteQueryOptions } from '@/shared/api/utils';

import type {
  CreateStaffRequest,
  Staff,
  StaffDepartmentResponse,
  StaffPositionResponse,
  StaffResponse,
  UpdateStaffRequest,
} from './types';

export const staffRtkApi = rtkApi.injectEndpoints({
  endpoints: (build) => ({
    getStaff: build.infiniteQuery<StaffResponse, void, PaginationFilter>({
      infiniteQueryOptions: pageInfiniteQueryOptions,

      query: ({ pageParam }) => {
        const params = getSearchParamsWithPagePagination(pageParam);

        return `/v1/auth/staff?${params}`;
      },

      providesTags: ['Staff'],
    }),

    getStaffById: build.query<Staff, number>({
      query(id) {
        return `/v1/auth/staff/${id}`;
      },
    }),

    createStaff: build.mutation<Staff, CreateStaffRequest>({
      query: (body) => ({
        url: '/v1/auth/staff',
        method: 'POST',
        body,
      }),

      invalidatesTags: ['Staff', 'Staff-position', 'Staff-department'],
    }),

    updateStaff: build.mutation<Staff, { id: number; body: UpdateStaffRequest }>({
      query: ({ id, body }) => ({
        url: `/v1/auth/staff/${id}`,
        method: 'PUT',
        body: body,
      }),

      invalidatesTags: ['Staff', 'Staff-position', 'Staff-department'],
    }),

    deleteStaff: build.mutation<void, number>({
      query: (id) => ({
        url: `/v1/auth/staff/${id}`,
        method: 'DELETE',
      }),

      invalidatesTags: ['Staff', 'Staff-position', 'Staff-department'],
    }),

    getStaffPositions: build.query<StaffPositionResponse, void, void>({
      query: () => {
        return '/v1/auth/staff/position';
      },

      providesTags: ['Staff-position'],
    }),

    getStaffDepartments: build.query<StaffDepartmentResponse, void, void>({
      query: () => {
        return '/v1/auth/staff/department';
      },

      providesTags: ['Staff-department'],
    }),
  }),
});

export const {
  useGetStaffInfiniteQuery,
  useGetStaffByIdQuery,
  useCreateStaffMutation,
  useUpdateStaffMutation,
  useDeleteStaffMutation,
  useGetStaffPositionsQuery,
  useGetStaffDepartmentsQuery,
} = staffRtkApi;
