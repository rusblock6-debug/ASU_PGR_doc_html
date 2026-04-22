import { rtkApi } from '@/shared/api/rtk-api';

import type { PlaceResponse } from './types';

export const placesApi = rtkApi.injectEndpoints({
  endpoints: (builder) => ({
    getPlace: builder.query<PlaceResponse, number>({
      query: (placeId) => `/api/places/${placeId}`,
      extraOptions: { backend: 'graph' as const },
      providesTags: (_result, _error, id) => [{ type: 'Place', id }],
    }),
  }),
});

export const { useGetPlaceQuery } = placesApi;
