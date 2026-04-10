import { rtkApi } from '@/shared/api';

import type {
  CreateRouteFleetControlRequest,
  DispatcherAssignmentVehicleRequest,
  FleetControlMutationResponse,
  FleetControlQueryArgs,
  FleetControlResponse,
  FleetControlRoutesResponse,
  FleetControlRouteStreamMessage,
  FleetControlVehicleTooltipResponse,
  ShiftLoadTypeVolumesQueryArgs,
  ShiftLoadTypeVolumesResponse,
  UpdateRouteFleetControlRequest,
} from './types';

const fleetControlRtkApi = rtkApi.injectEndpoints({
  endpoints: (builder) => ({
    getFleetControl: builder.query<FleetControlResponse, FleetControlQueryArgs | void>({
      query: (queryArg) => {
        const params = new URLSearchParams();

        if (queryArg?.route_id) {
          queryArg.route_id.forEach((id) => params.append('route_id', id));
        }

        const query = params.toString();
        return query ? `/fleet-control?${query}` : '/fleet-control';
      },

      providesTags: ['Fleet-control'],
    }),

    getFleetControlRoutes: builder.query<readonly FleetControlRoutesResponse[], void>({
      query: () => {
        return `/fleet-control/routes`;
      },

      providesTags: ['Fleet-control'],
    }),

    createRoute: builder.mutation<FleetControlMutationResponse, CreateRouteFleetControlRequest>({
      query: (body) => ({
        url: '/fleet-control/routes',
        method: 'POST',
        body,
      }),

      invalidatesTags: ['Fleet-control'],
    }),

    updateRoute: builder.mutation<FleetControlMutationResponse, UpdateRouteFleetControlRequest>({
      query: (body) => ({
        url: '/fleet-control/routes/update-places',
        method: 'POST',
        body,
      }),

      invalidatesTags: ['Fleet-control'],
    }),

    deleteRoute: builder.mutation<FleetControlMutationResponse, string>({
      query: (routeId) => ({
        url: `/fleet-control/routes/${routeId}`,
        method: 'DELETE',
      }),

      invalidatesTags: ['Fleet-control'],
    }),

    getVehicleTooltip: builder.query<FleetControlVehicleTooltipResponse, number>({
      query: (vehicleId) => {
        return `/fleet-control/vehicles/${vehicleId}/tooltip`;
      },

      providesTags: ['Fleet-control-vehicle-tooltip'],
    }),

    assignmentVehicle: builder.mutation<void, DispatcherAssignmentVehicleRequest>({
      query: (body) => ({
        url: '/fleet-control/assignments',
        method: 'POST',
        body,
      }),

      invalidatesTags: ['Fleet-control'],
    }),

    getShiftLoadTypeVolumes: builder.query<ShiftLoadTypeVolumesResponse, ShiftLoadTypeVolumesQueryArgs>({
      query: ({ section_id: sectionId, place_id: placeId }) => {
        const params = new URLSearchParams();

        if (sectionId) {
          sectionId.forEach((id) => params.append('section_id', String(id)));
        }

        if (placeId) {
          placeId.forEach((id) => params.append('place_id', String(id)));
        }

        return `/fleet-control/shift-load-type-volumes?${params}`;
      },

      providesTags: ['Fleet-control-shift-load-type-volumes'],
    }),

    /**
     * SSE-поток событий маршрутов.
     */
    getFleetControlRoutesStream: builder.query<FleetControlRouteStreamMessage[], void>({
      queryFn: () => ({ data: [] }),
      keepUnusedDataFor: 0,

      async onCacheEntryAdded(_, { updateCachedData, cacheDataLoaded, cacheEntryRemoved }) {
        const eventSource = new EventSource('/api/events/stream/routes');

        try {
          await cacheDataLoaded;

          eventSource.onmessage = (event: MessageEvent<string>) => {
            const data = JSON.parse(event.data) as FleetControlRouteStreamMessage[];

            updateCachedData(() => {
              if (Array.isArray(data)) {
                return data;
              }
            });
          };

          await cacheEntryRemoved;
        } finally {
          eventSource.close();
        }
      },
    }),
  }),
});

export const {
  useGetFleetControlQuery,
  useGetFleetControlRoutesQuery,
  useCreateRouteMutation,
  useUpdateRouteMutation,
  useDeleteRouteMutation,
  useGetVehicleTooltipQuery,
  useAssignmentVehicleMutation,
  useGetShiftLoadTypeVolumesQuery,
  useGetFleetControlRoutesStreamQuery,
} = fleetControlRtkApi;
