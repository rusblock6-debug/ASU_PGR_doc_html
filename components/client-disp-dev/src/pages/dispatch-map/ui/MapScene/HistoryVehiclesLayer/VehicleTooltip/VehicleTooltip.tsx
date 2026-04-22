import { useGetAllPlacesQuery } from '@/shared/api/endpoints/places';
import { useGetStateHistoryLastStateQuery } from '@/shared/api/endpoints/state-history';
import { useGetAllStatusesQuery } from '@/shared/api/endpoints/statuses';
import { NO_DATA } from '@/shared/lib/constants';
import { hasValue } from '@/shared/lib/has-value';
import { useTimezone } from '@/shared/lib/hooks/useTimezone';
import { Skeleton } from '@/shared/ui/Skeleton';
import { StatusIcon } from '@/shared/ui/StatusIcon';

import { MapTooltip } from '../../MapTooltip';

import styles from './VehicleTooltip.module.css';

/**
 * Представляет свойства компонента {@link VehicleTooltip}.
 */
interface VehicleTooltipProps {
  /** Идентификатор транспортного средства. */
  readonly id: number;
  /** Название транспортного средства. */
  readonly name: string;
  /** Время. */
  readonly timestamp: string;
  /** Скорость транспортного средства. */
  readonly speed: number | null;
  /** Остаток топлива транспортного средства. */
  readonly fuel: number | null;
  /** Объем топливного бака. */
  readonly tankVolume: number | null;
}

/**
 * Контент тултипа для маркера транспорта.
 */
export function VehicleTooltip({ id, name, timestamp, speed, fuel, tankVolume }: VehicleTooltipProps) {
  const { data: popupData } = useGetStateHistoryLastStateQuery({ vehicle_id: id, timestamp });
  const { data: statusesData } = useGetAllStatusesQuery();
  const { data: placesData } = useGetAllPlacesQuery();

  const tz = useTimezone();

  const status = hasValue(popupData?.state)
    ? statusesData?.items.find((status) => status.system_name === popupData.state)
    : null;

  const speedText = hasValue(speed) ? `${speed} км/ч` : NO_DATA.LONG_DASH;

  const currentPlace = hasValue(popupData?.place_id)
    ? placesData?.items.find((place) => place.id === popupData.place_id)
    : null;

  const fuelText = `${fuel ?? NO_DATA.LONG_DASH} л/ ${tankVolume ?? NO_DATA.LONG_DASH} л`;

  const placeText = currentPlace?.name ?? NO_DATA.LONG_DASH;

  return (
    <MapTooltip>
      <MapTooltip.Title>
        <span className={styles.title}>
          <span>{tz.format(timestamp, 'dd.MM.yyyy HH:mm:ss')}</span>
          <span>{name}</span>
        </span>
      </MapTooltip.Title>

      <MapTooltip.Body>
        <MapTooltip.Row label="Статус">
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

        <MapTooltip.Row label="Скорость">
          <Skeleton
            miw={150}
            visible={!popupData}
          >
            {speedText}
          </Skeleton>
        </MapTooltip.Row>

        <MapTooltip.Row label="Топливо">
          <Skeleton
            miw={150}
            visible={!popupData}
          >
            {fuelText}
          </Skeleton>
        </MapTooltip.Row>

        <MapTooltip.Row label="Место">
          <Skeleton
            miw={150}
            visible={!popupData}
          >
            {placeText}
          </Skeleton>
        </MapTooltip.Row>
      </MapTooltip.Body>
    </MapTooltip>
  );
}
