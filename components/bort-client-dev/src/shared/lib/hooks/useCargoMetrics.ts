import { useGetLoadTypeQuery } from '@/shared/api/endpoints/load-types';
import { useGetPlaceQuery } from '@/shared/api/endpoints/places';

/**
 * По place_b_id активного задания получает cargo_type из graph-service,
 * затем density из enterprise-service.
 */
export const useCargoMetrics = (placeId: number | null | undefined) => {
  const { data: place, isLoading: isPlaceLoading } = useGetPlaceQuery(placeId as number, {
    skip: placeId == null,
  });

  const cargoType = place?.cargo_type ?? null;

  const { data: loadType, isLoading: isLoadTypeLoading } = useGetLoadTypeQuery(cargoType as number, {
    skip: cargoType == null,
  });

  return {
    density: loadType?.density ?? null,
    cargoTypeName: loadType?.name ?? null,
    isLoading: isPlaceLoading || isLoadTypeLoading,
  };
};
