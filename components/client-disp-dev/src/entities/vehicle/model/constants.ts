import type { VehicleType } from '@/shared/api/endpoints/vehicles';
import { assertNever } from '@/shared/lib/assert-never';

import PDMImg from '../assets/icons/ic-pdm-orange.svg';
import SHASImg from '../assets/icons/ic-shas-orange.svg';
import PDMIcon from '../assets/icons/ic-vehicle-pdm.svg?react';
import SHASIcon from '../assets/icons/ic-vehicle-shas.svg?react';

/**
 * Список типов оборудования.
 * Используется для инициализации zod-схемы валидации.
 */
export const VEHICLE_TYPES = ['shas', 'pdm', 'vehicle'] as const satisfies readonly VehicleType[];

/** Значение {@link VehicleType} для случаев, когда тип машины отсутствует. */
export const DEFAULT_VEHICLE_TYPE = 'vehicle' as const satisfies VehicleType;

/** Типы оборудования доступные для выбора в UI (без служебного `vehicle`). */
export type SelectableVehicleType = Exclude<VehicleType, 'vehicle'>;

/** Маппинг типов оборудования на их отображаемые названия. */
export const VehicleTypeLabels = {
  shas: 'ШАС',
  pdm: 'ПДМ',
} as const satisfies Record<SelectableVehicleType, string>;

/** Опции для селекта типа оборудования. */
export const vehicleTypeOptions = Object.entries(VehicleTypeLabels).map(([value, label]) => ({ value, label }));

/**
 * Возвращает иконку типа транспортного средства с заданным цветом (оранжевый).
 * Используется для размещения в img теге.
 *
 * @param vehicleType тип транспортного средства.
 */
export function getVehicleTypeOrangeIcon(vehicleType: VehicleType) {
  switch (vehicleType) {
    case 'vehicle':
      return null;
    case 'pdm':
      return PDMImg;
    case 'shas':
      return SHASImg;
    default:
      assertNever(vehicleType);
  }
}

/**
 * Возвращает иконку типа транспортного средства.
 *
 * @param vehicleType тип транспортного средства.
 */
export function getVehicleTypeIcon(vehicleType: VehicleType) {
  switch (vehicleType) {
    case 'vehicle':
      return null;
    case 'pdm':
      return PDMIcon;
    case 'shas':
      return SHASIcon;
    default:
      assertNever(vehicleType);
  }
}

/**
 * Возвращает отображаемое имя типа транспортного средства.
 *
 * @param vehicleType тип транспортного средства.
 */
export function getVehicleTypeDisplayName(vehicleType: VehicleType) {
  switch (vehicleType) {
    case 'vehicle':
      return null;
    case 'pdm':
      return 'ПДМ';
    case 'shas':
      return 'ШАС';
    default:
      assertNever(vehicleType);
  }
}
