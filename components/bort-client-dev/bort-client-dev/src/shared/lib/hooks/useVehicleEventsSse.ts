import { useEffect } from 'react';

import { subscribeVehicleEventsSse } from '@/shared/api/sse/vehicle-events-sse';
import { VEHICLE_ID_STR } from '@/shared/config/env';
import { useAppDispatch } from '@/shared/lib/hooks/useAppDispatch';

/** Подписка на SSE событий борта для текущего `VEHICLE_ID`; отписывается при размонтировании. */
export const useVehicleEventsSse = () => {
  const dispatch = useAppDispatch();

  useEffect(() => {
    return subscribeVehicleEventsSse(dispatch, VEHICLE_ID_STR);
  }, [dispatch]);
};
