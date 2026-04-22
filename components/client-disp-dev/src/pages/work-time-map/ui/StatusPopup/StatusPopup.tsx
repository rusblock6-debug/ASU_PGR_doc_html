import { useEffect } from 'react';

import { useGetPlaceByIdQuery } from '@/shared/api/endpoints/places';
import { isCycleStateHistory, type StateHistory } from '@/shared/api/endpoints/state-history';
import { useLazyGetTripByIdQuery } from '@/shared/api/endpoints/trips';
import CrossIcon from '@/shared/assets/icons/ic-cross.svg?react';
import { cn } from '@/shared/lib/classnames-utils';
import { NO_DATA } from '@/shared/lib/constants';
import { calculateDuration, getTimeDurationDisplayValue } from '@/shared/lib/format-time-duration';
import { hasValue } from '@/shared/lib/has-value';
import { useElementPositioning } from '@/shared/lib/hooks/useElementPositioning';
import { useOutsideScroll } from '@/shared/lib/hooks/useOutsideScroll';
import { useTimezone } from '@/shared/lib/hooks/useTimezone';
import { AppButton } from '@/shared/ui/AppButton';
import { ContentString } from '@/shared/ui/ContentString';
import { StatusIcon } from '@/shared/ui/StatusIcon';
import type { ElementCoordinates } from '@/shared/ui/types';

import { getStatusSourceDisplayName } from '../../lib/get-status-source-display-name';
import { useWorkTimeMapPageContext } from '../../model/WorkTimeMapPageContext';

import styles from './StatusPopup.module.css';

/** Смещение всплывающего окна по оси У. */
const POPUP_OFFSET_Y = 30;

/** Представляет свойства компонента всплывающего окна с информацией и статусе. */
interface StatusPopupProps {
  /** Возвращает выбранный статус (элемент таймлайна). */
  readonly status: StateHistory;
  /** Возвращает следующий за выбранным статусом (элемент таймлайна). */
  readonly nextStatus: StateHistory | null;
  /** Возвращает координаты положения всплывающего окна. */
  readonly coordinates: ElementCoordinates;
  /** Возвращает делегат, вызываемый при закрытии всплывающего окна. */
  readonly onClose: () => void;
}

/**
 * Представляет компонент всплывающего окна с информацией и статусе.
 */
// eslint-disable-next-line sonarjs/cognitive-complexity
export function StatusPopup(props: StatusPopupProps) {
  const { status, nextStatus, coordinates, onClose } = props;
  const { statuses, vehicles } = useWorkTimeMapPageContext();

  const isCycleStatus = isCycleStateHistory(status);

  const hasCycleId = isCycleStatus && hasValue(status.cycle_id);

  const [
    fetchTrip,
    { data: tripFetchData, isLoading: isLoadingTrip, isFetching: isFetchingTrip, isError: isErrorTrip },
  ] = useLazyGetTripByIdQuery();

  useEffect(() => {
    void fetchTrip(hasCycleId ? status.cycle_id : null);
  }, [fetchTrip, hasCycleId, status, nextStatus]);

  const tripData = !isErrorTrip && !isFetchingTrip && hasCycleId ? tripFetchData : null;

  const {
    data: placeData,
    isLoading: isLoadingPlace,
    isFetching: isFetchingPlace,
  } = useGetPlaceByIdQuery(isCycleStatus ? status.place_id : null, {
    skip: !isCycleStatus || !hasValue(status.place_id),
  });

  const tz = useTimezone();

  const tooltipRef = useElementPositioning(coordinates, 0, POPUP_OFFSET_Y);

  useOutsideScroll(tooltipRef, onClose);

  const statusName = statuses.find((item) => item.system_name === status.state)?.display_name ?? NO_DATA.DASH;
  const statusColor = statuses.find((item) => item.system_name === status.state)?.color ?? '';
  const statusStartDate = tz.format(status.timestamp, 'dd.MM.yyyy');
  const statusStartTime = tz.format(status.timestamp, 'HH:mm:ss');

  const statusEndDate = nextStatus ? tz.format(nextStatus.timestamp, 'dd.MM.yyyy') : NO_DATA.DASH;
  const statusEndTime = nextStatus ? tz.format(nextStatus.timestamp, 'HH:mm:ss') : NO_DATA.DASH;
  const statusDuration = nextStatus
    ? getTimeDurationDisplayValue(calculateDuration(status.timestamp, nextStatus.timestamp))
    : NO_DATA.DASH;

  const statusCategory =
    statuses.find((item) => item.system_name === status.state)?.organization_category_name ?? NO_DATA.DASH;
  const statusSource = getStatusSourceDisplayName(status);

  const equipmentName = vehicles.find((item) => item.id === status.vehicle_id)?.name ?? NO_DATA.DASH;
  const statusPoint = isCycleStatus && status.place_id ? (placeData?.name ?? NO_DATA.DASH) : NO_DATA.DASH;

  const timeInWork =
    !isCycleStatus && hasValue(status.work_duration) && status.work_duration > 0
      ? getTimeDurationDisplayValue(status.work_duration * 1000)
      : NO_DATA.DASH;
  const timeNotInWork =
    !isCycleStatus && hasValue(status.idle_duration) && status.idle_duration > 0
      ? getTimeDurationDisplayValue(status.idle_duration * 1000)
      : NO_DATA.DASH;

  const cycleStartDate = hasValue(tripData?.cycle_started_at)
    ? tz.format(tripData.cycle_started_at, 'dd.MM.yyyy')
    : NO_DATA.DASH;
  const cycleStartTime = hasValue(tripData?.cycle_started_at)
    ? tz.format(tripData.cycle_started_at, 'HH:mm:ss')
    : NO_DATA.DASH;
  const cycleEndDate = hasValue(tripData?.cycle_completed_at)
    ? tz.format(tripData.cycle_completed_at, 'dd.MM.yyyy')
    : NO_DATA.DASH;
  const cycleEndTime = hasValue(tripData?.cycle_completed_at)
    ? tz.format(tripData.cycle_completed_at, 'HH:mm:ss')
    : NO_DATA.DASH;
  const cycleDuration =
    hasValue(tripData?.cycle_started_at) && hasValue(tripData?.cycle_completed_at)
      ? getTimeDurationDisplayValue(calculateDuration(tripData.cycle_started_at, tripData.cycle_completed_at))
      : NO_DATA.DASH;
  const cycleNumber = tripData?.cycle_num ? String(tripData.cycle_num) : NO_DATA.DASH;

  return (
    <div
      ref={tooltipRef}
      className={cn(styles.root, { [styles.small]: !isCycleStatus })}
    >
      <div className={styles.content}>
        <div className={styles.content_block}>
          <div className={styles.close_icon_container}>
            <AppButton
              size="s"
              variant="clear"
              onClick={onClose}
              fullWidth
              onlyIcon
            >
              <CrossIcon className={styles.close_icon} />
            </AppButton>
          </div>
          <p className={styles.block_title}>Информация о статусе</p>
          <ContentString
            title="Наименование статуса"
            values={[statusName]}
            afterElement={
              <div className={cn(styles.status_color_container, { [styles.small]: !isCycleStatus })}>
                <StatusIcon color={statusColor} />
              </div>
            }
            stringInfoClassName={!isCycleStatus ? styles.string_info : undefined}
          />
          {isCycleStatus && (
            <>
              <ContentString
                title="Начало статуса"
                values={[statusStartTime, statusStartDate]}
              />
              <ContentString
                title="Конец статуса"
                values={[statusEndTime, statusEndDate]}
              />
              <ContentString
                title="Продолжительность статуса"
                values={[statusDuration]}
              />
              <ContentString
                title="Категория статуса"
                values={[statusCategory]}
              />
            </>
          )}

          <ContentString
            title="Наименование техники"
            values={[equipmentName]}
          />

          {isCycleStatus && (
            <ContentString
              title="Источник статуса"
              values={[statusSource]}
            />
          )}

          {!isCycleStatus && (
            <>
              <ContentString
                title="Время «В работе»"
                values={[timeInWork]}
              />
              <ContentString
                title="Время «Не в работе»"
                values={[timeNotInWork]}
              />
            </>
          )}

          {isCycleStatus && (
            <ContentString
              title="Место фиксации статуса"
              values={[statusPoint]}
              isLoading={isLoadingPlace || isFetchingPlace}
            />
          )}
        </div>
        {isCycleStatus && (
          <div className={styles.content_block}>
            <p className={styles.block_title}>Информация о рейсе</p>
            <ContentString
              title="Начало рейса"
              values={[cycleStartTime, cycleStartDate]}
              isLoading={isLoadingTrip || isFetchingTrip}
            />
            <ContentString
              title="Конец рейса"
              values={[cycleEndTime, cycleEndDate]}
              isLoading={isLoadingTrip || isFetchingTrip}
            />
            <ContentString
              title="Продолжительность рейса"
              values={[cycleDuration]}
              isLoading={isLoadingTrip || isFetchingTrip}
            />
            <ContentString
              title="Номер рейса"
              values={[cycleNumber]}
              isLoading={isLoadingTrip || isFetchingTrip}
            />
          </div>
        )}
      </div>
    </div>
  );
}
