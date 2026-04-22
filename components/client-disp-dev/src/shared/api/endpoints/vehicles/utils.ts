import type { VehicleStateEvent } from './types';

/**
 * Проверяет, что значение соответствует элементу SSE-потока состояния машины.
 */
export function isVehicleStateEvent(value: unknown): value is VehicleStateEvent {
  if (typeof value !== 'object' || value === null) return false;

  const candidate = value as Partial<VehicleStateEvent>;
  return (
    candidate.event_type === 'vehicle_state' &&
    typeof candidate.vehicle_id === 'number' &&
    (typeof candidate.state === 'string' || candidate.state === null) &&
    (typeof candidate.horizon_id === 'number' || candidate.horizon_id === null) &&
    (typeof candidate.place_id === 'number' || candidate.place_id === null)
  );
}
