import { useGetAllPlacesQuery } from '@/shared/api/endpoints/places';
import { useGetAllStatusesQuery } from '@/shared/api/endpoints/statuses/statuses-rtk';
import { useGetVehiclePopupQuery } from '@/shared/api/endpoints/vehicles';
import { NO_DATA } from '@/shared/lib/constants';
import { hasValue } from '@/shared/lib/has-value';
import { Skeleton } from '@/shared/ui/Skeleton';
import { StatusIcon } from '@/shared/ui/StatusIcon';

import { MapTooltip } from '../../MapTooltip';

import styles from './VehicleTooltip.module.css';

/**
 * Представляет свойства компонента {@link VehicleTooltip}.
 */
interface VehicleTooltipProps {
  /** Идентификатор транспортного средства. */
  readonly vehicleId: number;
  /** Название транспортного средства. */
  readonly vehicleName: string;
}

/**
 * Контент тултипа для маркера транспорта.
 */
export function VehicleTooltip({ vehicleId, vehicleName }: VehicleTooltipProps) {
  const { data: popupData } = useGetVehiclePopupQuery(vehicleId, {
    pollingInterval: 5_000,
    refetchOnMountOrArgChange: true,
  });
  const { data: statusesData } = useGetAllStatusesQuery();
  const { data: placesData } = useGetAllPlacesQuery();

  const status = hasValue(popupData?.status_system_name)
    ? statusesData?.items.find((status) => status.system_name === popupData.status_system_name)
    : undefined;

  const placeStart = hasValue(popupData?.place_start_id)
    ? placesData?.items.find((place) => place.id === popupData.place_start_id)
    : undefined;

  const placeFinish = hasValue(popupData?.place_finish_id)
    ? placesData?.items.find((place) => place.id === popupData.place_finish_id)
    : undefined;

  const routeText =
    placeStart || placeFinish
      ? `${placeStart?.name ?? NO_DATA.LONG_DASH} → ${placeFinish?.name ?? NO_DATA.LONG_DASH}`
      : NO_DATA.LONG_DASH;

  const tripsText = hasValue(popupData?.planned_trips_count)
    ? `${popupData.actual_trips_count ?? 0} / ${popupData.planned_trips_count}`
    : NO_DATA.LONG_DASH;

  const weightText = hasValue(popupData?.weight) ? `${parseFloat(popupData.weight.toFixed(2))} т.` : NO_DATA.LONG_DASH;

  const speedText = hasValue(popupData?.speed) ? `${popupData.speed} км/ч` : NO_DATA.LONG_DASH;

  const currentPlace = hasValue(popupData?.current_places_id)
    ? placesData?.items.find((place) => place.id === popupData.current_places_id)
    : undefined;
  const placeText = currentPlace?.name ?? NO_DATA.LONG_DASH;

  return (
    <MapTooltip>
      <MapTooltip.Title>{vehicleName}</MapTooltip.Title>
      <MapTooltip.Body>
        <MapTooltip.Row label="Наименование статуса">
          <Skeleton visible={!popupData}>
            {status ? (
              <div className={styles.status}>
                {status.display_name}
                {status.color && <StatusIcon color={status.color} />}
              </div>
            ) : (
              NO_DATA.LONG_DASH
            )}
          </Skeleton>
        </MapTooltip.Row>

        <MapTooltip.Row label="Текущий маршрут">
          <Skeleton visible={!popupData}>{routeText}</Skeleton>
        </MapTooltip.Row>

        <MapTooltip.Row label="Рейсов выполнено">
          <Skeleton visible={!popupData}>{tripsText}</Skeleton>
        </MapTooltip.Row>

        <MapTooltip.Row label="Вес">
          <Skeleton visible={!popupData}>{weightText}</Skeleton>
        </MapTooltip.Row>

        <MapTooltip.Row label="Скорость">
          <Skeleton visible={!popupData}>{speedText}</Skeleton>
        </MapTooltip.Row>

        <MapTooltip.Row label="Местоположение">
          <Skeleton visible={!popupData}>{placeText}</Skeleton>
        </MapTooltip.Row>
      </MapTooltip.Body>
    </MapTooltip>
  );
}
