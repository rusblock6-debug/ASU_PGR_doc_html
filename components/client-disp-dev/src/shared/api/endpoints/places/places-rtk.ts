import { rtkApi } from '@/shared/api';
import type { PaginationFilter } from '@/shared/api/types';
import { getSearchParamsWithPagePagination, pageInfiniteQueryOptions } from '@/shared/api/utils';

import type {
  Place,
  PlaceCreateRequest,
  PlacePatchRequest,
  PlacePopupResponse,
  PlacesQueryArgs,
  PlacesResponse,
} from './types';

export const placeRtkApi = rtkApi.injectEndpoints({
  endpoints: (build) => ({
    getAllPlaces: build.query<PlacesResponse, PlacesQueryArgs | void>({
      query(queryArg) {
        const params = new URLSearchParams();

        if (queryArg?.type) {
          params.append('type', queryArg.type);
        }
        if (queryArg?.types) {
          params.append('types', queryArg.types.join(','));
        }
        if (queryArg?.is_active !== undefined) {
          params.append('is_active', queryArg.is_active.toString());
        }

        const query = params.toString();
        return query ? `/graph/places?${query}` : '/graph/places';
      },

      providesTags: ['Places'],
    }),

    getPlaces: build.infiniteQuery<PlacesResponse, PlacesQueryArgs | void, PaginationFilter>({
      infiniteQueryOptions: pageInfiniteQueryOptions,

      query: ({ queryArg, pageParam }) => {
        const params = getSearchParamsWithPagePagination(pageParam);

        if (queryArg?.type) {
          params.append('type', queryArg.type);
        }
        if (queryArg?.types) {
          params.append('types', queryArg.types.join(','));
        }
        if (queryArg?.is_active !== undefined) {
          params.append('is_active', queryArg.is_active.toString());
        }

        return `/graph/places?${params}`;
      },

      providesTags: ['Places'],
    }),

    getPlaceById: build.query<Place, number | null>({
      query(id) {
        return `/graph/places/${id}`;
      },
    }),

    createPlace: build.mutation<Place, PlaceCreateRequest>({
      query: (body) => ({
        url: '/graph/places',
        method: 'POST',
        body,
      }),

      invalidatesTags: ['Places'],
    }),

    updatePlace: build.mutation<Place, { placeId: number; body: PlacePatchRequest }>({
      query: ({ placeId, body }) => ({
        url: `/graph/places/${placeId}`,
        method: 'PATCH',
        // Отправка поля source необходима для сервера. Чтобы сервер понимал, что это отправлено с клиента, а не из другого сервиса.
        body: { ...body, source: 'dispatcher' },
      }),

      invalidatesTags: ['Places'],
    }),

    deletePlace: build.mutation<void, number>({
      query: (placeId) => ({
        url: `/graph/places/${placeId}`,
        method: 'DELETE',
      }),

      invalidatesTags: ['Places'],
    }),

    getPlacePopup: build.query<PlacePopupResponse, number>({
      query: (placeId) => `/graph/places/popup/${placeId}`,
      providesTags: ['Places'],
    }),
  }),
});

export const {
  useGetAllPlacesQuery,
  useGetPlacesInfiniteQuery,
  useGetPlaceByIdQuery,
  useCreatePlaceMutation,
  useUpdatePlaceMutation,
  useDeletePlaceMutation,
  useGetPlacePopupQuery,
} = placeRtkApi;
