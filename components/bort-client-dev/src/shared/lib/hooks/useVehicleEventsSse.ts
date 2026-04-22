import { useSubscribeVehicleEventsStreamQuery } from '@/shared/api/endpoints/vehicle-state';
import { VEHICLE_ID_STR } from '@/shared/config/env';

/** Подписка на SSE событий борта через RTK Query streaming endpoint. */
export const useVehicleEventsSse = () => {
  useSubscribeVehicleEventsStreamQuery(VEHICLE_ID_STR);
};
