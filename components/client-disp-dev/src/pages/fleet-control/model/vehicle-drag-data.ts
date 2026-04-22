import type { AssignPlaceType } from '@/shared/api/endpoints/fleet-control';
import type { VehicleType } from '@/shared/api/endpoints/vehicles';
import { hasValue } from '@/shared/lib/has-value';

/**
 * Представляет данные передаваемые при захвате элемента.
 */
export interface VehicleDragData {
  /** Возвращает тип перемещения. */
  readonly moveType: 'vehicle-drag';
  /** Возвращает тип оборудования. */
  readonly vehicleType: VehicleType;
  /** Возвращает идентификатор оборудования. */
  readonly vehicleId: number;
  /** Возвращает наименование оборудования. */
  readonly vehicleName: string;
  /** Возвращает цвет иконки оборудования. */
  readonly vehicleColor?: string;
  /** Возвращает текущее место расположения. */
  readonly currentAssignedPlace?: AssignPlaceType;
  /** Возвращает идентификатор текущего места погрузки. */
  readonly currentRoutePlaceAId: number | null;
  /** Возвращает идентификатор текущего места разгрузки. */
  readonly currentRoutePlaceBId: number | null;
  /** Возвращает идентификатор текущего гаража. */
  readonly currentGarageId: number | null;
}

/**
 * Проверяет, является ли переданный объект, объектом типа VehicleDragData. Сужает тип, до гарантированно являющегося VehicleDragData.
 *
 * @param data проверяемый объект.
 */
export function isVehicleDragData(data?: object): data is VehicleDragData {
  return hasValue(data) && 'moveType' in data && data.moveType === 'vehicle-drag';
}
