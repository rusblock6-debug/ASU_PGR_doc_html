import { createEntityAdapter } from '@reduxjs/toolkit';

import { rtkApi } from '@/shared/api';
import type { PaginationFilter } from '@/shared/api/types';
import {
  createAuthenticatedSSE,
  getSearchParamsWithPagePagination,
  pageInfiniteQueryOptions,
} from '@/shared/api/utils';
import { DEFAULT_ENTERPRISE_ID } from '@/shared/config/constants';

import type {
  CreateVehicleRequest,
  NormalizedVehiclesResponse,
  UpdateVehicleParams,
  Vehicle,
  VehicleCoordinates,
  VehiclePlacesResponse,
  VehiclePopupResponse,
  VehiclesQueryArg,
  VehiclesResponse,
  VehicleStateEvent,
  VehicleStateResponse,
} from './types';
import { isVehicleStateEvent } from './utils';
import { createVehicleTrackingWS } from './vehicle-tracking-ws';

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

        return `/enterprise/vehicles?${params}`;
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

        return `/enterprise/vehicles?${params}`;
      },

      providesTags: ['Vehicle'],
    }),

    getVehicleById: build.query<Vehicle, number>({
      query: (id) => ({
        url: `/enterprise/vehicles/${id}`,
      }),
    }),

    createVehicle: build.mutation<Vehicle, CreateVehicleRequest>({
      query: (body) => ({
        url: '/enterprise/vehicles',
        method: 'POST',
        body,
      }),
      invalidatesTags: ['Vehicle'],
    }),

    updateVehicle: build.mutation<Vehicle, UpdateVehicleParams>({
      query: ({ id, body }) => ({
        url: `/enterprise/vehicles/${id}`,
        method: 'PUT',
        body,
      }),
      invalidatesTags: ['Vehicle'],
    }),

    deleteVehicle: build.mutation<void, number>({
      query: (id) => ({
        url: `/enterprise/vehicles/${id}`,
        method: 'DELETE',
      }),
      invalidatesTags: ['Vehicle'],
    }),

    getVehiclePlaces: build.query<VehiclePlacesResponse, void>({
      query: () => '/graph/vehicles/places',
      providesTags: ['Vehicle'],
    }),

    getVehicleState: build.query<VehicleStateResponse, void>({
      query: () => '/graph/vehicles/state',
      providesTags: ['Vehicle'],
    }),

    getVehiclePopup: build.query<VehiclePopupResponse, number>({
      query: (vehicleId) => `/graph/vehicles/popup/${vehicleId}`,
      providesTags: ['Vehicle'],
    }),

    getVehiclesStream: build.query<Record<number, VehicleStateEvent>, void>({
      queryFn: () => ({ data: {} }),
      keepUnusedDataFor: 0,

      async onCacheEntryAdded(_, { updateCachedData, cacheDataLoaded, cacheEntryRemoved, dispatch }) {
        await createAuthenticatedSSE({
          url: '/graph/events/stream/vehicles',
          dispatch,
          cacheDataLoaded,
          cacheEntryRemoved,
          onMessage(data) {
            if (!Array.isArray(data)) return;

            const events = data.filter(isVehicleStateEvent);
            if (events.length === 0) return;

            updateCachedData((draft) => {
              for (const item of events) {
                draft[item.vehicle_id] = item;
              }
            });
          },
        });
      },
    }),

    /**
     * Подписка на координаты машин через WebSocket `/ws/vehicle-tracking`.
     *
     * Координаты приходят отдельными сообщениями — по одному на машину.
     * Чтобы не обновлять React-дерево на каждое сообщение, координаты
     * накапливаются в буфере и применяются пачкой перед следующей
     * отрисовкой кадра (`requestAnimationFrame`). Это важно
     * при возврате из фоновой вкладки, когда браузер доставляет
     * накопившиеся WS-сообщения разом.
     *
     * Когда вкладка в фоне, `requestAnimationFrame` приостанавливается,
     * а буфер продолжает заполняться. При возврате накопленные
     * координаты применяются за раз. Размер буфера ограничен числом машин,
     * потому что повторное сообщение от той же машины перезатирает предыдущее.
     */
    getVehicleCoordinatesStream: build.query<Record<number, VehicleCoordinates>, void>({
      queryFn: () => ({ data: {} }),
      keepUnusedDataFor: 0,

      onCacheEntryAdded: async function (_, { updateCachedData, cacheDataLoaded, cacheEntryRemoved }) {
        let buffer: Record<number, VehicleCoordinates> = {};
        let rafId: number | null = null;

        const flush = () => {
          const batch = buffer;
          buffer = {};
          rafId = null;

          updateCachedData((draft) => {
            for (const key in batch) {
              draft[Number(key)] = batch[Number(key)];
            }
          });
        };

        const vehicleTracker = createVehicleTrackingWS((vehicleId, lat, lon) => {
          buffer[vehicleId] = { vehicle_id: vehicleId, lat, lon };
          if (rafId === null) rafId = requestAnimationFrame(flush);
        });

        try {
          await cacheDataLoaded;
          vehicleTracker.start();
          await cacheEntryRemoved;
        } finally {
          if (rafId !== null) cancelAnimationFrame(rafId);
          vehicleTracker.dispose();
        }
      },
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
  useGetVehiclesStreamQuery,
  useGetVehicleCoordinatesStreamQuery,
  useCreateVehicleMutation,
  useUpdateVehicleMutation,
  useDeleteVehicleMutation,
} = vehicleRtkApi;
