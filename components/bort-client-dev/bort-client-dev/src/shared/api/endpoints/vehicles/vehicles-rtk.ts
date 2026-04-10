import { enterpriseApi } from '@/shared/api/enterprise-api';

/** DTO техники из enterprise-service. */
export interface VehicleResponse {
  readonly id: number;
  readonly name: string;
  readonly [key: string]: unknown;
}

export const vehiclesApi = enterpriseApi.injectEndpoints({
  endpoints: (builder) => ({
    getVehicleById: builder.query<VehicleResponse, number>({
      query: (id) => `/api/vehicles/${id}`,
      providesTags: (_result, _error, id) => [{ type: 'Vehicle' as const, id }],
    }),
  }),
});

export const { useGetVehicleByIdQuery } = vehiclesApi;
