import { VehicleCard, VehicleCardSkeleton } from '../VehicleCard';

import styles from './WorkOrderContent.module.css';

/**
 * Представляет свойства для компонента контента страницы «Наряд-задание».
 */
interface WorkOrderContentProps {
  /** Флаг загрузки первоначальных данных страницы. */
  readonly isInitialLoading: boolean;
  /** Флаг блокировки всего контента.*/
  readonly isDisabled: boolean;
  /** Флаг наличия ошибки при загрузке данных. */
  readonly isError: boolean;
  /** Флаг наличия данных для отображения. */
  readonly hasData: boolean;
  /** ID техники, для которой отображаем карточки. */
  readonly vehicleIds: readonly number[];
  /** Список подсвеченных транспортных средств. */
  readonly highlightedVehicleIds: ReadonlySet<number>;
}

/**
 * Контент страницы «Наряд-задание»: заглушки состояний и список карточек техники.
 */
export function WorkOrderContent({
  isInitialLoading,
  isDisabled,
  isError,
  hasData,
  vehicleIds,
  highlightedVehicleIds,
}: WorkOrderContentProps) {
  if (isInitialLoading) {
    return <VehicleCardSkeleton />;
  }

  if (isError || !hasData) {
    return <p className={styles.message}>Ничего не найдено</p>;
  }

  return (
    <>
      {vehicleIds.map((vehicleId, index) => (
        <VehicleCard
          key={vehicleId}
          vehicleId={vehicleId}
          isDisabled={isDisabled}
          isFirstElement={index === 0}
          isLastElement={index === vehicleIds.length - 1}
          isHighlighted={highlightedVehicleIds.has(vehicleId)}
        />
      ))}
    </>
  );
}
