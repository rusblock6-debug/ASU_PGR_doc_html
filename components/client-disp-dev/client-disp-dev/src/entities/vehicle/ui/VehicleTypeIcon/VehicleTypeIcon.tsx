import type { SVGProps } from 'react';

import type { VehicleType } from '@/shared/api/endpoints/vehicles';

import { getVehicleTypeIcon } from '../../model/constants';

/**
 * Представляет свойства для компонента {@link VehicleTypeIcon}.
 * Наследуются от стандартных SVG-пропсов, плюс обязательный `vehicleType`.
 */
interface VehicleTypeIconProps extends SVGProps<SVGSVGElement> {
  /** Тип транспортного средства. */
  readonly vehicleType: VehicleType;
}

/**
 * Представляет компонент иконки в соответствии с типом техники.
 * Если для переданного `vehicleType` иконки нет, ничего не отображает.
 */
export function VehicleTypeIcon({ vehicleType, ...props }: VehicleTypeIconProps) {
  const Icon = getVehicleTypeIcon(vehicleType);
  if (!Icon) return null;

  return <Icon {...props} />;
}
