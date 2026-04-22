import { useGetAllHorizonsQuery } from '@/shared/api/endpoints/horizons';
import {
  useGetAllVehiclesQuery,
  useGetVehiclePlacesQuery,
  useGetVehiclesStreamQuery,
  type Vehicle,
} from '@/shared/api/endpoints/vehicles';
import { EMPTY_ARRAY } from '@/shared/lib/constants';
import { hasValue } from '@/shared/lib/has-value';
import { useAppSelector } from '@/shared/lib/hooks/useAppSelector';
import { sortByField } from '@/shared/lib/sort-by-field';

import { selectHorizonFilter, selectSelectedHorizonId, selectVehicleGroupSorts } from '../../model/selectors';
import { HorizonFilter } from '../../model/types';
import type { VehicleGroupKey } from '../../model/types';

/** Тип техники с добавленным именем горизонта. */
export type MapVehicleItem = Vehicle & {
  /** Наименование горизонта. */
  readonly horizon_name: string;
  /** Идентификатор горизонта, на котором находится техника. */
  readonly horizon_id: number | null;
};

/**
 * Хук для получения данных техники для карты: название горизонта и ID, группы ПДМ/ШАС, сортировка по параметрам из Redux.
 */
export function useMapVehicles() {
  const { data: allVehicles, isLoading: isVehiclesLoading } = useGetAllVehiclesQuery();
  const { data: vehiclePlacementsData, isLoading: isPlacementsLoading } = useGetVehiclePlacesQuery();
  const { data: sseStream } = useGetVehiclesStreamQuery();
  const { data: allHorizonsData } = useGetAllHorizonsQuery();
  const sorts = useAppSelector(selectVehicleGroupSorts);
  const horizonFilter = useAppSelector(selectHorizonFilter);
  const selectedHorizonId = useAppSelector(selectSelectedHorizonId);

  const isLoading = isVehiclesLoading || isPlacementsLoading;

  const placementsById = new Map(
    (vehiclePlacementsData?.items ?? EMPTY_ARRAY).map((place) => {
      return [place.vehicle_id, place];
    }),
  );

  const horizonsMap = new Map<number, number>(
    (allHorizonsData?.items ?? EMPTY_ARRAY).map((horizon) => [horizon.id, horizon.height]),
  );

  const all = Object.values(allVehicles?.entities ?? {})
    .filter((vehicle) => vehicle.is_active)
    .map((vehicle) => {
      const sseEvent = sseStream?.[vehicle.id];
      const horizonId = sseEvent?.horizon_id ?? placementsById.get(vehicle.id)?.horizon_id ?? null;
      const horizonHeight = hasValue(horizonId) ? horizonsMap.get(horizonId) : null;

      return {
        ...vehicle,
        horizon_name: typeof horizonHeight === 'number' ? `${horizonHeight} м` : '',
        horizon_id: horizonId,
      };
    });

  const filteredAll =
    horizonFilter === HorizonFilter.CURRENT_HORIZON
      ? all.filter((vehicle) => vehicle.horizon_id === selectedHorizonId)
      : all;

  const { pdm, shas } = filteredAll.reduce<Record<VehicleGroupKey, MapVehicleItem[]>>(
    (acc, vehicle) => {
      if (vehicle.vehicle_type === 'pdm') acc.pdm.push(vehicle);
      else if (vehicle.vehicle_type === 'shas') acc.shas.push(vehicle);
      return acc;
    },
    { pdm: [], shas: [] },
  );

  const groups = {
    pdm: sortByField(pdm, sorts.pdm),
    shas: sortByField(shas, sorts.shas),
  };

  return { groups, all: filteredAll, isLoading, sorts };
}
