import type { VehicleType } from '@/shared/api/endpoints/vehicles';

/**
 * Представляет базовую модель перемещаемого элемента
 */
interface DraggableBaseElement {
  /** Возвращает идентификатор. */
  readonly id: string;
  /** Возвращает тип перемещаемого элемента. */
  readonly elementType: 'route' | 'vehicle';
}

/**
 * Представляет перемещаемый маршрут.
 */
interface DraggableRoute extends DraggableBaseElement {
  /** Возвращает тип перемещаемого элемента. */
  readonly elementType: 'route';
}

/**
 * Представляет перемещаемое оборудование.
 */
interface DraggableVehicle extends DraggableBaseElement {
  /** Возвращает тип перемещаемого элемента. */
  readonly elementType: 'vehicle';
  /** Возвращает идентификатор оборудования. */
  readonly vehicleId: number;
  /** Возвращает наименование оборудования. */
  readonly vehicleName: string;
  /** Возвращает тип оборудования. */
  readonly vehicleType: VehicleType;
  /** Возвращает цвет иконки оборудования. */
  readonly vehicleColor?: string;
}

/**
 * Представляет перемещаемый элемент.
 */
export type DraggableElement = DraggableRoute | DraggableVehicle;

/**
 * Проверяет, является ли перемещаемый элемент, элемент типа DraggableVehicle. Сужает тип, до гарантированно являющегося DraggableVehicle.
 *
 * @param element перемещаемый элемент.
 */
export function isDraggableVehicle(element: DraggableElement | null): element is DraggableVehicle {
  return element?.elementType === 'vehicle';
}

/**
 * Проверяет, является ли перемещаемый элемент, элемент типа DraggableRoute. Сужает тип, до гарантированно являющегося DraggableRoute.
 *
 * @param element перемещаемый элемент.
 */
export function isDraggableRoute(element: DraggableElement | null): element is DraggableRoute {
  return element?.elementType === 'route';
}
