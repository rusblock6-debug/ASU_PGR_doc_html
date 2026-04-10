import { selectVehicleById, VehicleTypeIcon } from '@/entities/vehicle';

import { hasValue } from '@/shared/lib/has-value';
import { useAppSelector } from '@/shared/lib/hooks/useAppSelector';

import styles from './VehicleCard.module.css';

/**
 * Пропсы компонента {@link VehicleTitle}.
 */
interface VehicleNameProps {
  /** Идентификатор техники, для которой нужно отобразить название и иконку. */
  readonly vehicleId: number;
}

/**
 * Отображает название и иконку техники по её идентификатору.
 */
export function VehicleTitle({ vehicleId }: VehicleNameProps) {
  const vehicle = useAppSelector((state) => selectVehicleById(state, vehicleId));
  if (!hasValue(vehicle)) return null;

  return (
    <div className={styles.vehicle_title}>
      <VehicleTypeIcon
        className={styles.vehicle_icon}
        vehicleType={vehicle.vehicle_type}
        width={30}
      />
      {vehicle.name}
    </div>
  );
}
