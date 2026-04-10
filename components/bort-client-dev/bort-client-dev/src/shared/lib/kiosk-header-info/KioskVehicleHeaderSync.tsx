import { useEffect } from 'react';
import { useSelector } from 'react-redux';

import { useGetPlaceQuery } from '@/shared/api/endpoints/places';
import { useGetTagByIdQuery } from '@/shared/api/endpoints/tags';
import { useGetVehicleStateQuery } from '@/shared/api/endpoints/vehicle-state';
import type { VehicleState } from '@/shared/api/types/vehicle-events';
import { NO_DATA } from '@/shared/lib/constants';
import { formatLastTransitionTime24 } from '@/shared/lib/format-last-transition';
import { useAppDispatch } from '@/shared/lib/hooks/useAppDispatch';
import { selectStateChangedAt, stateEventReceived } from '@/shared/lib/vehicle-events';

import { useKioskHeaderInfo } from './KioskHeaderInfoContext';

const POLL_MS = 30_000;

const VEHICLE_STATES = new Set<string>([
  'idle',
  'moving_empty',
  'stopped_empty',
  'loading',
  'moving_loaded',
  'stopped_loaded',
  'unloading',
]);

/**
 * Центр шапки: имя места (GET /graph-api/api/places/:last_place_id), иначе имя тега (last_tag_id),
 * плюс время last_transition (24ч, локаль).
 * Засевает vehicleEventsSlice из GET /state, если SSE ещё не доставил state_event.
 */
export function KioskVehicleHeaderSync() {
  const dispatch = useAppDispatch();
  const { setHeaderInfo } = useKioskHeaderInfo();
  const { data: state } = useGetVehicleStateQuery(undefined, { pollingInterval: POLL_MS });

  const rawPlaceId = state?.last_place_id;
  let placeId: number | undefined;
  if (rawPlaceId == null || rawPlaceId === '') {
    placeId = undefined;
  } else {
    const n = typeof rawPlaceId === 'number' ? rawPlaceId : Number(String(rawPlaceId).trim());
    placeId = Number.isFinite(n) ? n : undefined;
  }

  const rawTagId = state?.last_tag_id;
  const tagId = rawTagId == null || rawTagId === '' ? '' : String(rawTagId).trim();

  const {
    data: place,
    isLoading: isPlaceLoading,
    fulfilledTimeStamp: placeFulfilled,
    isError: isPlaceError,
  } = useGetPlaceQuery(placeId as number, {
    skip: placeId == null,
    refetchOnMountOrArgChange: true,
  });

  const {
    data: tag,
    isLoading: isTagLoading,
    fulfilledTimeStamp,
    isError,
  } = useGetTagByIdQuery(tagId, {
    skip: !tagId,
    refetchOnMountOrArgChange: true,
  });
  const stateChangedAt = useSelector(selectStateChangedAt);

  useEffect(() => {
    const rawState = state?.state;
    const rawTs = state?.last_transition;
    if (!rawState || !VEHICLE_STATES.has(rawState) || !rawTs) return;

    const polledTs = typeof rawTs === 'number' ? new Date(rawTs).toISOString() : String(rawTs);

    const storedMs = stateChangedAt ? new Date(stateChangedAt).getTime() : null;
    const polledMs = new Date(polledTs).getTime();

    if (storedMs == null || polledMs > storedMs) {
      dispatch(
        stateEventReceived({ event_type: 'state_event', status: rawState as VehicleState, timestamp: polledTs }),
      );
    }
  }, [dispatch, state?.state, state?.last_transition, stateChangedAt]);

  useEffect(() => {
    const nameFromPlace = typeof place?.name === 'string' ? place.name.trim() : '';
    const nameFromTag = typeof tag?.name === 'string' ? tag.name.trim() : '';
    const resolved = nameFromPlace || nameFromTag;

    let locationLabel: string = NO_DATA.LONG_DASH;
    if (placeId != null || tagId) {
      if (resolved) {
        locationLabel = resolved;
      } else {
        const waiting = (placeId != null && isPlaceLoading) || (Boolean(tagId) && isTagLoading);
        locationLabel = waiting ? NO_DATA.ELLIPSIS : NO_DATA.LONG_DASH;
      }
    }

    const locationSubLabel = formatLastTransitionTime24(state?.last_transition);

    setHeaderInfo({ locationLabel, locationSubLabel });
  }, [
    setHeaderInfo,
    state?.last_transition,
    place?.name,
    placeId,
    isPlaceLoading,
    placeFulfilled,
    isPlaceError,
    tag?.name,
    tagId,
    isTagLoading,
    fulfilledTimeStamp,
    isError,
  ]);

  return null;
}
