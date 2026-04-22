import { rtkApi } from '@/shared/api/rtk-api';

import type { LoadTypeResponse } from './types';

export const loadTypesApi = rtkApi.injectEndpoints({
  endpoints: (builder) => ({
    getLoadType: builder.query<LoadTypeResponse, number>({
      query: (id) => `/api/load_types/${id}`,
      extraOptions: { backend: 'enterprise' as const },
      providesTags: (_result, _error, id) => [{ type: 'LoadType', id }],
    }),
  }),
});

export const { useGetLoadTypeQuery } = loadTypesApi;
