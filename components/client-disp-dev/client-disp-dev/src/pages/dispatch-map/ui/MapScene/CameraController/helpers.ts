import type { Place } from '@/shared/api/endpoints/places';

import { toScene } from '../../../lib/coordinates';
import type { FocusTarget } from '../../../model/types';
import type { VehicleData } from '../VehiclesLayer';

/**
 * Определяет координаты точки фокуса камеры для выбранной сущности.
 *
 * @param focusTarget цель для фокусировки камеры.
 * @param vehicles данные техники.
 * @param places данные мест.
 * @returns Координаты сцены или `null`, если цель не найдена/некорректна.
 */
export function resolveTargetPosition(
  focusTarget: FocusTarget,
  vehicles?: Record<string, VehicleData>,
  places?: readonly Place[],
) {
  if (focusTarget.entity === 'vehicle') {
    return resolveVehicleTargetPosition(focusTarget.id, vehicles);
  }

  return resolvePlaceTargetPosition(focusTarget.id, places);
}

/**
 * Возвращает позицию фокусировки камеры для техники в координатах сцены.
 *
 * @param focusTargetId id техники для фокусировки камеры.
 * @param vehicles данные техники.
 * @returns координаты сцены или `null`, если техника не найдена/некорректна.
 */
function resolveVehicleTargetPosition(focusTargetId: number, vehicles?: Record<string, VehicleData>) {
  if (!vehicles) return null;

  const vehicle = Object.values(vehicles).find((value) => value.vehicle_id === focusTargetId);
  if (!vehicle || (vehicle.lat === 0 && vehicle.lon === 0)) return null;

  return toScene(vehicle.lon, vehicle.lat);
}

/**
 * Возвращает позицию фокусировки камеры для места в координатах сцены.
 *
 * @param focusTargetId id места для фокусировки камеры.
 * @param places данные мест.
 * @returns координаты сцены или `null`, если место не найдено/некорректно.
 */
function resolvePlaceTargetPosition(focusTargetId: number, places?: readonly Place[]) {
  if (!places) return null;

  const place = places.find((item) => item.id === focusTargetId);
  if (!place) return null;

  const lon = Number(place.x);
  const lat = Number(place.y);
  if (!Number.isFinite(lon) || !Number.isFinite(lat)) return null;

  return toScene(lon, lat);
}
