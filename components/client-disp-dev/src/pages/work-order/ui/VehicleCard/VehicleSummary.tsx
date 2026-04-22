import { formatNumber } from '@/shared/lib/format-number';
import { useAppSelector } from '@/shared/lib/hooks/useAppSelector';

import { selectVehicleAggregates } from '../../model/selectors';

import styles from './VehicleCard.module.css';

/**
 * Представляет свойства компонента {@link VehicleSummary}.
 */
interface VehicleSummaryProps {
  /** Идентификатор техники. */
  readonly vehicleId: number;
}

/**
 * Представляет компонент агрегированных показателей по маршрутным заданиям машины:
 * суммарный объём (м³), вес (тонн) и количество рейсов.
 */
export function VehicleSummary({ vehicleId }: VehicleSummaryProps) {
  const { volume, weight, trips } = useAppSelector((state) => selectVehicleAggregates(state, vehicleId));

  const formattedVolumes = volume > 0 ? `${formatNumber(volume)} м³` : '0';
  const formattedWeights = weight > 0 ? `${formatNumber(weight)} тонн` : '0';
  const formattedTrips = trips > 0 ? formatNumber(trips) : '0';

  return (
    <>
      <p className={styles.summary}>
        <span className={styles.summary_label}>Объем, м³</span>
        <span className={styles.summary_field}>{formattedVolumes}</span>
      </p>
      <p className={styles.summary}>
        <span className={styles.summary_label}>Вес, т</span>
        <span className={styles.summary_field}>{formattedWeights}</span>
      </p>
      <p className={styles.summary}>
        <span className={styles.summary_label}>Рейсов</span>
        <span className={styles.summary_field}>{formattedTrips}</span>
      </p>
    </>
  );
}
