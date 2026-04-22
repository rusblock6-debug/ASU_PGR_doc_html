import { rtkApi } from '@/shared/api';

import type { CreateShaftsRequest, Shaft, ShaftsResponse, UpdateShaftRequest } from './types';

export const shaftsRtkApi = rtkApi.injectEndpoints({
  endpoints: (builder) => ({
    getAllShafts: builder.query<ShaftsResponse, void>({
      query: () => {
        return '/graph/shafts';
      },

      providesTags: ['Shafts'],
    }),

    createShaft: builder.mutation<Shaft, CreateShaftsRequest>({
      query: (body) => ({
        url: '/graph/shafts',
        method: 'POST',
        body,
      }),

      invalidatesTags: ['Shafts'],
    }),

    updateShaft: builder.mutation<Shaft, { id: number; body: UpdateShaftRequest }>({
      query: ({ id, body }) => ({
        url: `/graph/shafts/${id}`,
        method: 'PATCH',
        body,
      }),

      invalidatesTags: ['Shafts'],
    }),

    deleteShaft: builder.mutation<void, number>({
      query: (shaftId) => ({
        url: `/graph/shafts/${shaftId}`,
        method: 'DELETE',
      }),

      invalidatesTags: ['Shafts'],
    }),
  }),
});

export const { useGetAllShaftsQuery, useCreateShaftMutation, useUpdateShaftMutation, useDeleteShaftMutation } =
  shaftsRtkApi;
