import { useGetPlaceQuery } from '@/shared/api/endpoints/places';

/**
 * Имена мест A/B из GET /graph-api/api/places/:id (кэш RTK Query).
 */
export const useRouteTaskPlaceNames = (placeAId: number, placeBId: number, options?: { readonly skip?: boolean }) => {
  const skip = options?.skip ?? false;
  const { data: placeA } = useGetPlaceQuery(placeAId, { skip: skip || !placeAId });
  const { data: placeB } = useGetPlaceQuery(placeBId, { skip: skip || !placeBId });

  return {
    placeAName: placeA?.name ?? null,
    placeBName: placeB?.name ?? null,
  };
};
