import type { AssignPlaceType } from '@/shared/api/endpoints/fleet-control';
import { hasValue } from '@/shared/lib/has-value';

/**
 * Представляет данные передаваемые при окончании перемещения элемента.
 */
export interface VehicleDropData {
  /** Возвращает тип перемещения. */
  readonly moveType: 'vehicle-drop';
  /** Возвращает тип целевого места. */
  readonly targetKind: AssignPlaceType;
  /** Возвращает идентификатор целевого места погрузки. */
  readonly targetRoutePlaceAId?: number | null;
  /** Возвращает идентификатор целевого места разгрузки. */
  readonly targetRoutePlaceBId?: number | null;
  /** Возвращает идентификатор целевого гаража. */
  readonly targetGarageId?: number | null;
}

/**
 * Проверяет, является ли переданный объект, объектом типа VehicleDropData. Сужает тип, до гарантированно являющегося VehicleDropData.
 *
 * @param data проверяемый объект.
 */
export function isVehicleDropData(data?: object): data is VehicleDropData {
  return hasValue(data) && 'moveType' in data && data.moveType === 'vehicle-drop';
}
