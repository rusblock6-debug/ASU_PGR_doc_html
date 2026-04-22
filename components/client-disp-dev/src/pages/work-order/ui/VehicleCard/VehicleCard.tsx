import { shallowEqual } from 'react-redux';

import { selectVehicleStatus } from '@/entities/vehicle';

import AddIcon from '@/shared/assets/icons/ic-icon-plus.svg?react';
import { cn } from '@/shared/lib/classnames-utils';
import { useAppDispatch } from '@/shared/lib/hooks/useAppDispatch';
import { useAppSelector } from '@/shared/lib/hooks/useAppSelector';
import { AppButton } from '@/shared/ui/AppButton';
import { Select } from '@/shared/ui/Select';

import { useRouteTaskData } from '../../lib/hooks/useRouteTaskData';
import { selectMergedVehicleTaskIds, selectVehicleHasError, selectVehicleHasWarning } from '../../model/selectors';
import { workOrderActions } from '../../model/slice';
import { RouteTask, RouteTaskSkeleton } from '../RouteTask';

import styles from './VehicleCard.module.css';
import { VehicleSummary } from './VehicleSummary';
import { VehicleTitle } from './VehicleTitle';

/**
 * Представляет свойства компонента {@link VehicleCard}.
 */
interface VehicleCardProps {
  /** Идентификатор транспортного средства. */
  readonly vehicleId: number;
  /** Указывает, является ли элемент первым в списке. */
  readonly isFirstElement?: boolean;
  /** Указывает, является ли элемент последним в списке. */
  readonly isLastElement?: boolean;
  /** Включает подсветку карточки при обновлении данных. */
  readonly isHighlighted?: boolean;
  /** Блокирует всю карточку. */
  readonly isDisabled?: boolean;
}

/**
 * Представляет карточку транспортного средства.
 */
export function VehicleCard({ vehicleId, isFirstElement, isLastElement, isHighlighted, isDisabled }: VehicleCardProps) {
  const vehicleStatus = useAppSelector((state) => selectVehicleStatus(state, vehicleId));
  const hasRepairStatus = vehicleStatus === 'repair';

  const taskIds = useAppSelector((state) => selectMergedVehicleTaskIds(state, vehicleId), shallowEqual);
  const hasError = useAppSelector((state) => selectVehicleHasError(state, vehicleId));
  const hasWarning = useAppSelector((state) => selectVehicleHasWarning(state, vehicleId));

  const routeTaskData = useRouteTaskData(vehicleId);

  const dispatch = useAppDispatch();

  const handleAddNewRouteTask = () => {
    dispatch(workOrderActions.addTask({ vehicleId }));
  };

  return (
    <div
      className={cn(styles.vehicle_card, {
        [styles.first]: isFirstElement,
        [styles.last]: isLastElement,
        [styles.disabled]: isDisabled,
        [styles.maintenance]: hasRepairStatus,
        [styles.validation_error]: hasError,
        [styles.validation_warning]: hasWarning && !hasError,
        [styles.highlighted]: isHighlighted,
      })}
    >
      <div className={styles.vehicle}>
        <div className={styles.vehicle_sticky}>
          <VehicleTitle vehicleId={vehicleId} />

          <div className={styles.vehicle_summary}>
            {hasRepairStatus && (
              <p className={styles.summary}>
                <span className={styles.summary_label}>Статус</span>
                <span className={styles.summary_field}>В ремонте</span>
              </p>
            )}
            <Select
              classNames={{
                root: cn(styles.summary, styles.summary_gap),
                label: styles.summary_label,
              }}
              withAsterisk
              withCheckIcon={false}
              variant="combobox-primary"
              inputSize="combobox-xs"
              labelPosition="horizontal"
              label="Оператор"
              placeholder="Укажите"
              value="1"
              data={[{ label: 'Борзунов О.А.', value: '1' }]}
              searchable
            />
            <VehicleSummary vehicleId={vehicleId} />
          </div>
        </div>
      </div>

      <div className={styles.vehicle_action}>
        <AppButton
          variant="primary"
          size="xs"
          onlyIcon
          onClick={handleAddNewRouteTask}
        >
          <AddIcon
            width={12}
            height={12}
          />
          <span className="g-screen-reader-only">Добавить задание</span>
        </AppButton>
      </div>

      <div className={styles.vehicle_routes}>
        {taskIds.length > 0 ? (
          taskIds.map((taskId) => (
            <RouteTask
              key={taskId}
              taskId={taskId}
              vehicleId={vehicleId}
              routeTaskData={routeTaskData}
            />
          ))
        ) : (
          <RouteTaskSkeleton />
        )}
      </div>
    </div>
  );
}
