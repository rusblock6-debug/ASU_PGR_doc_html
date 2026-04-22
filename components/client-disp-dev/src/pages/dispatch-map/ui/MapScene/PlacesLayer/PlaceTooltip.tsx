import { useGetAllLoadTypeQuery } from '@/shared/api/endpoints/load-types';
import type { Place } from '@/shared/api/endpoints/places';
import { useGetPlacePopupQuery } from '@/shared/api/endpoints/places';
import { useGetAllVehiclesQuery } from '@/shared/api/endpoints/vehicles';
import { EMPTY_ARRAY, NO_DATA } from '@/shared/lib/constants';
import { hasValue } from '@/shared/lib/has-value';
import { Skeleton } from '@/shared/ui/Skeleton';

import { MapTooltip } from '../MapTooltip';

/**
 * Представляет свойства компонента {@link PlaceTooltip}.
 */
interface PlaceTooltipProps {
  /** Идентификатор места. */
  readonly placeId: number;
  /** Название места. */
  readonly placeName: string;
  /** Вид груза. */
  readonly cargoType: Place['cargo_type'];
}

/**
 * Контент тултипа для маркера места.
 */
export function PlaceTooltip({ placeId, placeName, cargoType }: PlaceTooltipProps) {
  const { data: popupData } = useGetPlacePopupQuery(placeId, {
    pollingInterval: 5_000,
    refetchOnMountOrArgChange: true,
  });
  const { data: cargoData } = useGetAllLoadTypeQuery();
  const { data: allVehicles } = useGetAllVehiclesQuery();

  const cargo = hasValue(cargoType) ? cargoData?.entities[cargoType] : undefined;
  const vehicles = popupData?.vehicle_id_list?.map((vehicleId) => allVehicles?.entities[vehicleId]) ?? EMPTY_ARRAY;
  const vehiclesNames = vehicles.map((vehicle) => vehicle?.name ?? '');

  return (
    <MapTooltip>
      <MapTooltip.Title>{placeName}</MapTooltip.Title>
      <MapTooltip.Body>
        <MapTooltip.Row label="Вид груза">
          <Skeleton visible={!popupData}>{cargo?.name ?? NO_DATA.LONG_DASH}</Skeleton>
        </MapTooltip.Row>
        <MapTooltip.Row label="Остаток">
          <Skeleton visible={!popupData}>{popupData?.current_stock ?? NO_DATA.LONG_DASH}</Skeleton>
        </MapTooltip.Row>
        <MapTooltip.Row label="План / факт">
          <Skeleton visible={!popupData}>
            {popupData?.planned_value ?? NO_DATA.LONG_DASH} / {popupData?.real_value ?? NO_DATA.LONG_DASH}
          </Skeleton>
        </MapTooltip.Row>
        <MapTooltip.Row label="Техника в зоне">
          <Skeleton visible={!popupData}>
            {vehiclesNames.length ? vehiclesNames.join(', ') : NO_DATA.LONG_DASH}
          </Skeleton>
        </MapTooltip.Row>
      </MapTooltip.Body>
    </MapTooltip>
  );
}
