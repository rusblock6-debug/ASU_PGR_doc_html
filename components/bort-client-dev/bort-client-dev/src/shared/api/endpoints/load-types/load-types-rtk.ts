import { enterpriseApi } from '@/shared/api/enterprise-api';

/** DTO типа груза из enterprise-service. */
export interface LoadTypeResponse {
  readonly id: number;
  readonly name: string;
  readonly density: number | null;
  readonly [key: string]: unknown;
}

export const loadTypesApi = enterpriseApi.injectEndpoints({
  endpoints: (builder) => ({
    getLoadType: builder.query<LoadTypeResponse, number>({
      query: (id) => `/api/load_types/${id}`,
      providesTags: (_result, _error, id) => [{ type: 'LoadType', id }],
    }),
  }),
});

export const { useGetLoadTypeQuery } = loadTypesApi;
