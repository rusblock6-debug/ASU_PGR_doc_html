import type { Place } from '@/shared/api/endpoints/places';

/**
 * Представляет модель перемещаемого оборудования.
 */
export interface MovingVehicle {
  /** Возвращает идентификатор оборудования. */
  readonly vehicleId: number;
  /** Возвращает заголовок. */
  readonly title: string;
  /** Возвращает целевой пункт погрузки. */
  readonly targetPlaceLoad: Place | null;
  /** Возвращает целевой пункт разгрузки. */
  readonly targetPlaceUnload: Place | null;
  /** Возвращает делегат, вызываемый при подтверждении перемещения. */
  readonly moveFn: () => void;
}
