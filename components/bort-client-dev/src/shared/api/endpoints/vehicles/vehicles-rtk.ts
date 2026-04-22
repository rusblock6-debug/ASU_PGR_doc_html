import { rtkApi } from '@/shared/api/rtk-api';

import type { VehicleResponse } from './types';

export const vehiclesApi = rtkApi.injectEndpoints({
  endpoints: (builder) => ({
    getVehicleById: builder.query<VehicleResponse, number>({
      query: (id) => `/api/vehicles/${id}`,
      extraOptions: { backend: 'enterprise' as const },
      providesTags: (_result, _error, id) => [{ type: 'Vehicle' as const, id }],
    }),
  }),
});

export const { useGetVehicleByIdQuery } = vehiclesApi;
