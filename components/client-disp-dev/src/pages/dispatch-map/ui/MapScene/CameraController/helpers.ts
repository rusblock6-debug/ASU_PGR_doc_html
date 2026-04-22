import type { Place } from '@/shared/api/endpoints/places';

import { toScene } from '../../../lib/coordinates';
import type { VehicleMapStateItem } from '../../../lib/hooks/useMapVehicleRealtimeState';
import type { FocusTarget } from '../../../model/types';

/**
 * Определяет координаты точки фокуса камеры для выбранной сущности.
 *
 * @param focusTarget цель для фокусировки камеры.
 * @param vehicleMapState состояние машины.
 * @param places данные мест.
 * @returns Координаты сцены или `null`, если цель не найдена/некорректна.
 */
export function resolveTargetPosition(
  focusTarget: FocusTarget,
  vehicleMapState: Record<number, VehicleMapStateItem>,
  places?: readonly Place[],
) {
  if (focusTarget.entity === 'vehicle') {
    return vehicleMapState[focusTarget.id]?.scenePosition ?? null;
  }

  return resolvePlaceTargetPosition(focusTarget.id, places);
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
