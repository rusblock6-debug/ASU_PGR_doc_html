import { useGetAllHorizonsQuery } from '@/shared/api/endpoints/horizons';
import {
  useGetAllVehiclesQuery,
  useGetVehiclePlacesQuery,
  type Vehicle,
  type VehiclePlaceItem,
} from '@/shared/api/endpoints/vehicles';
import { EMPTY_ARRAY } from '@/shared/lib/constants';
import { useAppSelector } from '@/shared/lib/hooks/useAppSelector';
import { sortByField } from '@/shared/lib/sort-by-field';

import { selectVehicleGroupSorts } from '../../model/selectors';
import type { VehicleGroupKey } from '../../model/types';

/** Тип техники с добавленным именем горизонта. */
export type MapVehicleItem = Vehicle & {
  /** Наименование горизонта. */
  readonly horizon_name: string;
  /** Идентификатор горизонта, на котором находится техника. */
  readonly horizon_id: number | null;
};

/**
 * Хук для получения данных техники для карты: подпись горизонта, группы ПДМ/ШАС, сортировка по параметрам из Redux.
 */
export function useMapVehicles() {
  const { data: allVehicles, isLoading } = useGetAllVehiclesQuery();
  const { data: vehiclePlacesData } = useGetVehiclePlacesQuery();
  const { data: allHorizonsData } = useGetAllHorizonsQuery();
  const sorts = useAppSelector(selectVehicleGroupSorts);

  const vehiclePlacesMap = new Map<number, VehiclePlaceItem>(
    (vehiclePlacesData?.items ?? EMPTY_ARRAY).map((item) => [item.vehicle_id, item]),
  );

  const horizonsMap = new Map<number, number>(
    (allHorizonsData?.items ?? EMPTY_ARRAY).map((horizon) => [horizon.id, horizon.height]),
  );

  const all = Object.values(allVehicles?.entities ?? {}).map((vehicle) => {
    const place = vehiclePlacesMap.get(vehicle.id);
    const horizonHeight = place ? horizonsMap.get(place.horizon_id) : undefined;

    return {
      ...vehicle,
      horizon_name: typeof horizonHeight === 'number' ? `${horizonHeight} м` : '',
      horizon_id: place?.horizon_id ?? null,
    };
  });

  const { pdm, shas } = all.reduce<Record<VehicleGroupKey, MapVehicleItem[]>>(
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

  return { groups, all, isLoading, sorts };
}
