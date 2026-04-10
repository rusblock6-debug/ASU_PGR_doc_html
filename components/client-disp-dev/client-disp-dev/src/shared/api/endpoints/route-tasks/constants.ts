import type { VehicleType } from '@/shared/api/endpoints/vehicles';

/**
 * Статусы маршрутного задания.
 */
export const RouteStatus = {
  EMPTY: 'empty',
  SENT: 'sent',
  ACTIVE: 'active',
  PAUSED: 'paused',
  DELIVERED: 'delivered',
  COMPLETED: 'completed',
  REJECTED: 'rejected',
} as const;

/**
 * Строковое значение типа маршрутного задания.
 */
export type RouteTaskStatus = (typeof RouteStatus)[keyof typeof RouteStatus];

/**
 * Типы заданий для маршрутов.
 * Примечание: «погрузка в ШАС» доступна только для ПДМ.
 */
export const TypeTask = {
  /** Погрузка в ШАС (только для ПДМ) */
  LOADING_SHAS: 'loading_shas',
  /** Погрузка/транспортировка ГМ */
  LOADING_GM: 'loading_transport_gm',
  /** Хозяйственные рейсы */
  HOUSEKEEPING_TRIPS: 'housekeeping_trips',
} as const;

/**
 * Строковое значение типа задания.
 */
export type TypeTaskValue = (typeof TypeTask)[keyof typeof TypeTask];

/**
 * Все доступные типы заданий с правилами фильтрации по типу техники.
 */
const TASK_TYPE_OPTIONS: {
  /** Значение для отправки на сервер. */
  value: TypeTaskValue;
  /** Отображаемое название. */
  label: string;
  /** Доступно только для этих типов техники. undefined = для всех. */
  vehicleTypes?: VehicleType[];
}[] = [
  { value: TypeTask.LOADING_GM, label: 'Погрузка/транспортировка ГМ' },
  { value: TypeTask.HOUSEKEEPING_TRIPS, label: 'Хоз. рейсы' },
  { value: TypeTask.LOADING_SHAS, label: 'Погрузка в ШАС', vehicleTypes: ['pdm'] },
] as const;

/**
 * Получить опции для выпадающего списка «Тип задания» с учетом типа техники.
 * Если `vehicleType` не указан — возвращаются только опции без ограничений
 * (опции с `vehicleTypes` будут убраны).
 *
 * @param vehicleType Тип техники для фильтрации опций.
 * @returns Отфильтрованный список опций.
 */
export function getTaskTypeOptions(vehicleType?: VehicleType) {
  return TASK_TYPE_OPTIONS.filter(
    (option) => !option.vehicleTypes || (vehicleType && option.vehicleTypes.includes(vehicleType)),
  );
}
