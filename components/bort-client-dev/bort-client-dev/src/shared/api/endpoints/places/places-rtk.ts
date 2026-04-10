import { graphApi } from '@/shared/api/graph-api';

/** DTO места из graph-service. */
export interface PlaceResponse {
  readonly id: number;
  readonly name: string;
  readonly cargo_type: number | null;
  readonly node_id?: number | null;
  readonly location?: { lon: number; lat: number } | null;
  readonly [key: string]: unknown;
}

export const placesApi = graphApi.injectEndpoints({
  endpoints: (builder) => ({
    getPlace: builder.query<PlaceResponse, number>({
      query: (placeId) => `/api/places/${placeId}`,
      providesTags: (_result, _error, id) => [{ type: 'Place', id }],
    }),
  }),
});

export const { useGetPlaceQuery } = placesApi;
