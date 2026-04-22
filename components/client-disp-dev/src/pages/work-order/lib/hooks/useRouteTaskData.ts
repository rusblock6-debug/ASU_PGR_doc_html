import { useGetAllLoadTypeQuery } from '@/shared/api/endpoints/load-types';
import { useGetAllPlacesQuery } from '@/shared/api/endpoints/places';
import { getTaskTypeOptions } from '@/shared/api/endpoints/route-tasks';
import { useGetAllVehiclesQuery } from '@/shared/api/endpoints/vehicles';
import { EMPTY_ARRAY } from '@/shared/lib/constants';

export type RouteTaskData = ReturnType<typeof useRouteTaskData>;

/**
 * Хук для получения данных маршрутного задания.
 *
 * Возвращает:
 * - `placeLoadOptions` опции для выпадающего списка с местами погрузки.
 * - `placeUnloadOptions` опции для выпадающего списка с местами разгрузки.
 * - `taskTypeOptions` опции для выпадающего списка с типами заданий.
 * - `places` список мест.
 * - `cargoData` данные о грузах.
 */
export function useRouteTaskData(vehicleId: number) {
  const { data: placesData } = useGetAllPlacesQuery();
  const { data: cargoData } = useGetAllLoadTypeQuery();
  const { data: vehiclesData } = useGetAllVehiclesQuery();

  const places = placesData?.items?.length ? placesData.items : EMPTY_ARRAY;

  const placeLoadOptions = places
    .filter((item) => item.type === 'load' && item.is_active)
    .map((item) => ({ value: String(item.id), label: item.name }))
    .sort((a, b) => a.label.localeCompare(b.label, 'ru'));

  const placeUnloadOptions = places
    .filter((item) => item.type === 'unload' && item.is_active)
    .map((item) => ({ value: String(item.id), label: item.name }))
    .sort((a, b) => a.label.localeCompare(b.label, 'ru'));

  const vehicle = vehiclesData?.entities[vehicleId];
  const taskTypeOptions = getTaskTypeOptions(vehicle?.vehicle_type);

  return {
    places,
    cargoData,
    placeLoadOptions,
    placeUnloadOptions,
    taskTypeOptions,
  };
}
