import { rtkApi } from '@/shared/api';
import type { PaginationFilter } from '@/shared/api/types';
import { getSearchParamsWithPagePagination, pageInfiniteQueryOptions } from '@/shared/api/utils';

import type { CreateTripRequest, Trip, TripsQueryArg, TripsResponse, UpdateTripRequest } from './types';

export const tripRtkApi = rtkApi.injectEndpoints({
  endpoints: (build) => ({
    getTrips: build.infiniteQuery<TripsResponse, TripsQueryArg, PaginationFilter>({
      infiniteQueryOptions: pageInfiniteQueryOptions,

      query({ queryArg, pageParam }) {
        const params = getSearchParamsWithPagePagination(pageParam);

        const completedOnly = queryArg?.completed_only ?? false;
        params.append('completed_only', completedOnly.toString());

        if (queryArg?.vehicle_id) {
          params.append('vehicle_id', String(queryArg.vehicle_id));
        }
        if (queryArg?.task_id) {
          params.append('task_id', queryArg.task_id);
        }
        if (queryArg?.status) {
          params.append('status', queryArg.status);
        }
        if (queryArg?.trip_type) {
          params.append('trip_type', queryArg.trip_type);
        }
        if (queryArg?.from_date) {
          params.append('from_date', queryArg.from_date);
        }
        if (queryArg?.to_date) {
          params.append('to_date', queryArg.to_date);
        }

        return `/trips?${params}`;
      },

      providesTags: ['Trips'],

      // Сбрасываем кеш при смене фильтров (даты)
      keepUnusedDataFor: 0,
    }),

    getTripById: build.query<Trip, string | null>({
      query(id) {
        return `/trips/${id}`;
      },
    }),

    createTrip: build.mutation<Trip, CreateTripRequest>({
      query: (body) => ({
        url: '/trips',
        method: 'POST',
        body,
      }),
      invalidatesTags: ['Trips'],
    }),

    updateTrip: build.mutation<Trip, { tripId: string; body: UpdateTripRequest }>({
      query: ({ tripId, body }) => ({
        url: `/trips/${tripId}`,
        method: 'PUT',
        body,
      }),
      invalidatesTags: ['Trips'],
    }),

    deleteTrip: build.mutation<void, string>({
      query: (tripId) => ({
        url: `/trips/${tripId}`,
        method: 'DELETE',
      }),
      invalidatesTags: ['Trips'],
    }),
  }),
});

export const {
  useGetTripsInfiniteQuery,
  useGetTripByIdQuery,
  useLazyGetTripByIdQuery,
  useCreateTripMutation,
  useUpdateTripMutation,
  useDeleteTripMutation,
} = tripRtkApi;
