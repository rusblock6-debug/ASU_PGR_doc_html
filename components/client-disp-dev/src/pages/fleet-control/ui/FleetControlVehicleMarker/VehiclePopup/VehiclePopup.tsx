import { useMemo } from 'react';

import { useGetVehicleTooltipQuery } from '@/shared/api/endpoints/fleet-control';
import { useGetAllStatusesQuery } from '@/shared/api/endpoints/statuses';
import CrossIcon from '@/shared/assets/icons/ic-cross.svg?react';
import { EMPTY_ARRAY, NO_DATA } from '@/shared/lib/constants';
import { calculateDuration, getTimeDurationDisplayValue } from '@/shared/lib/format-time-duration';
import { hasValue } from '@/shared/lib/has-value';
import { useTimezone } from '@/shared/lib/hooks/useTimezone';
import { AppButton } from '@/shared/ui/AppButton';
import { ContentString } from '@/shared/ui/ContentString';
import { StatusIcon } from '@/shared/ui/StatusIcon';

import { POLLING_INTERVAL } from '../../../model/constants';

import styles from './VehiclePopup.module.css';

/**
 * Представляет свойства компонента всплывающего окна с информацией о технике.
 */
interface VehiclePopupProps {
  /** Возвращает идентификатор оборудования. */
  readonly vehicleId: number;
  /** Возвращает наименование. */
  readonly name: string;
  /** Возвращает делегат/, вызываемый при закрытии всплывающего окна. */
  readonly onClose: () => void;
}

/**
 * Представляет компонент всплывающего окна с информацией о технике.
 */
export function VehiclePopup({ vehicleId, name, onClose }: VehiclePopupProps) {
  const tz = useTimezone();

  const { data: vehicleTooltipData, isLoading: isLoadingVehicleTooltipData } = useGetVehicleTooltipQuery(vehicleId, {
    refetchOnMountOrArgChange: true,
    pollingInterval: POLLING_INTERVAL.OFTEN,
  });

  const { data: statusesData, isLoading: isLoadingStatusesData } = useGetAllStatusesQuery();

  const statuses = statusesData?.items ?? EMPTY_ARRAY;

  const vehicleStatus = statuses.find((status) => status.system_name === vehicleTooltipData?.state);

  const statusDuration = getTimeDurationDisplayValue((vehicleTooltipData?.state_duration ?? 0) * 1000);

  const statusNameInfo = `${vehicleStatus?.display_name} (${statusDuration})`;

  const tripCompleteCount = `${vehicleTooltipData?.actual_trips_count ?? NO_DATA.DASH} / ${vehicleTooltipData?.planned_trips_count ?? NO_DATA.DASH}`;

  const weight = `${vehicleTooltipData?.weight ?? 0} т`;

  const speed = `${vehicleTooltipData?.speed ?? 0} км/ ч`;

  const placeName = vehicleTooltipData?.place_name ?? NO_DATA.DASH;

  const lastMessageTimeAgo = useMemo(() => {
    const duration = hasValue(vehicleTooltipData?.last_message_timestamp)
      ? calculateDuration(vehicleTooltipData.last_message_timestamp, new Date())
      : null;

    const showedDuration = hasValue(duration) && duration > POLLING_INTERVAL.OFTEN * 2 ? duration : 0;

    return getTimeDurationDisplayValue(showedDuration);
  }, [vehicleTooltipData?.last_message_timestamp]);

  const lastMessageTime = useMemo(
    () =>
      hasValue(vehicleTooltipData?.last_message_timestamp)
        ? `${tz.format(vehicleTooltipData.last_message_timestamp, 'HH:mm:ss')} (${lastMessageTimeAgo} назад)`
        : NO_DATA.DASH,
    [tz, vehicleTooltipData?.last_message_timestamp, lastMessageTimeAgo],
  );

  const isLoading = isLoadingVehicleTooltipData || isLoadingStatusesData;

  return (
    <div className={styles.root}>
      <AppButton
        className={styles.close_button}
        size="s"
        variant="clear"
        onClick={onClose}
        fullWidth
        onlyIcon
      >
        <CrossIcon className={styles.close_icon} />
      </AppButton>
      <div className={styles.content}>
        <p className={styles.title}>{name}</p>
        <ContentString
          title="Наименование статуса"
          values={[statusNameInfo]}
          afterElement={
            <div className={styles.status_color_container}>
              <StatusIcon color={vehicleStatus?.color ?? ''} />
            </div>
          }
          stringInfoClassName={styles.string_info}
          isLoading={isLoading}
        />
        <ContentString
          title="Рейсов выполнено"
          values={[tripCompleteCount]}
          isLoading={isLoading}
        />
        <ContentString
          title="Вес"
          values={[weight]}
          isLoading={isLoading}
        />
        <ContentString
          title="Скорость"
          values={[speed]}
          isLoading={isLoading}
        />
        <ContentString
          title="Местоположение"
          values={[placeName]}
          isLoading={isLoading}
        />
        <ContentString
          title="Время последней связи"
          values={[lastMessageTime]}
          isLoading={isLoading}
        />
      </div>
    </div>
  );
}
