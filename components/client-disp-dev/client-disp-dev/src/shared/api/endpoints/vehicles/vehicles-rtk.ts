import { createEntityAdapter } from '@reduxjs/toolkit';

import { rtkApi } from '@/shared/api';
import type { PaginationFilter } from '@/shared/api/types';
import { getSearchParamsWithPagePagination, pageInfiniteQueryOptions } from '@/shared/api/utils';
import { DEFAULT_ENTERPRISE_ID } from '@/shared/config/constants';

import type {
  UpdateVehicleParams,
  Vehicle,
  VehiclePlacesResponse,
  VehiclePopupResponse,
  VehicleStateResponse,
  VehiclesQueryArg,
  VehiclesResponse,
  CreateVehicleRequest,
  NormalizedVehiclesResponse,
} from './types';

/**
 * Адаптер для нормализации данных транспорта с id как ключом.
 * Используется для выпадающих списков (TripEditorPage и др.).
 */
const vehiclesAdapter = createEntityAdapter({
  selectId: (vehicle: Vehicle) => vehicle.id,
});

export const vehicleRtkApi = rtkApi.injectEndpoints({
  endpoints: (build) => ({
    /**
     * Запрос для получения всех транспортов с нормализацией.
     * Используется для выпадающих списков (TripEditorPage и др.).
     */
    getAllVehicles: build.query<NormalizedVehiclesResponse, VehiclesQueryArg | void>({
      query(queryArg) {
        const params = new URLSearchParams();

        const enterpriseId = queryArg?.enterprise_id ?? DEFAULT_ENTERPRISE_ID;
        params.append('enterprise_id', String(enterpriseId));

        if (queryArg?.vehicle_type) {
          params.append('vehicle_type', queryArg.vehicle_type);
        }

        return `/vehicles?${params}`;
      },

      transformResponse: (response: VehiclesResponse): NormalizedVehiclesResponse => {
        const entityState = vehiclesAdapter.setAll(vehiclesAdapter.getInitialState(), response.items);
        return {
          ...entityState,
          total: response.total,
          page: response.page,
          size: response.size,
          pages: response.pages,
        };
      },

      providesTags: ['Vehicle'],
    }),

    /**
     * Запрос для получения списка транспорта с бесконечным скроллом.
     */
    getVehicles: build.infiniteQuery<VehiclesResponse, VehiclesQueryArg, PaginationFilter>({
      infiniteQueryOptions: pageInfiniteQueryOptions,

      query({ queryArg, pageParam }) {
        const params = getSearchParamsWithPagePagination(pageParam);

        const enterpriseId = queryArg?.enterprise_id ?? DEFAULT_ENTERPRISE_ID;
        params.append('enterprise_id', String(enterpriseId));

        if (queryArg?.vehicle_type) {
          params.append('vehicle_type', queryArg.vehicle_type);
        }

        return `/vehicles?${params}`;
      },

      providesTags: ['Vehicle'],
    }),

    getVehicleById: build.query<Vehicle, number>({
      query: (id) => ({
        url: `/vehicles/${id}`,
      }),
    }),

    createVehicle: build.mutation<Vehicle, CreateVehicleRequest>({
      query: (body) => ({
        url: '/vehicles',
        method: 'POST',
        body,
      }),
      invalidatesTags: ['Vehicle'],
    }),

    updateVehicle: build.mutation<Vehicle, UpdateVehicleParams>({
      query: ({ id, body }) => ({
        url: `/vehicles/${id}`,
        method: 'PUT',
        body,
      }),
      invalidatesTags: ['Vehicle'],
    }),

    deleteVehicle: build.mutation<void, number>({
      query: (id) => ({
        url: `/vehicles/${id}`,
        method: 'DELETE',
      }),
      invalidatesTags: ['Vehicle'],
    }),

    getVehiclePlaces: build.query<VehiclePlacesResponse, void>({
      query: () => '/vehicles/places',
      providesTags: ['Vehicle'],
    }),

    getVehicleState: build.query<VehicleStateResponse, void>({
      query: () => '/vehicles/state',
      providesTags: ['Vehicle'],
    }),

    getVehiclePopup: build.query<VehiclePopupResponse, number>({
      query: (vehicleId) => `/vehicles/popup/${vehicleId}`,
      providesTags: ['Vehicle'],
    }),
  }),
});

export const {
  useGetVehiclesInfiniteQuery,
  useGetAllVehiclesQuery,
  useGetVehiclePlacesQuery,
  useGetVehicleStateQuery,
  useGetVehiclePopupQuery,
  useGetVehicleByIdQuery,
  useCreateVehicleMutation,
  useUpdateVehicleMutation,
  useDeleteVehicleMutation,
} = vehicleRtkApi;
