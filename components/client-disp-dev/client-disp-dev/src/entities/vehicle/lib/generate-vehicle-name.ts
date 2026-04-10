import type { VehicleType } from '@/shared/api/endpoints/vehicles';
import { hasValue, hasValueNotEmpty } from '@/shared/lib/has-value';

import { getVehicleTypeDisplayName } from '../model/constants';

/**
 * Генерирует название оборудования.
 *
 * @param vehicleType Тип оборудования.
 * @param registrationNumber Гаражный номер (опционально).
 * @returns Название не более 100 символов.
 */
export function generateVehicleName(vehicleType: VehicleType, registrationNumber?: string | null) {
  const MAX_VEHICLE_NAME_LENGTH = 100;

  const label = getVehicleTypeDisplayName(vehicleType);
  if (!hasValueNotEmpty(registrationNumber) && hasValue(label)) return label.slice(0, MAX_VEHICLE_NAME_LENGTH);
  return `${label} №${registrationNumber}`.slice(0, MAX_VEHICLE_NAME_LENGTH);
}
