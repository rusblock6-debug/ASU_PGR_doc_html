import { type ReactNode, useState } from 'react';

import type { AssignPlaceType, VehicleFleetControl } from '@/shared/api/endpoints/fleet-control';
import { useGetAllStatusesQuery } from '@/shared/api/endpoints/statuses';
import ArrowIcon from '@/shared/assets/icons/ic-arrow-down.svg?react';
import { cn } from '@/shared/lib/classnames-utils';
import { EMPTY_ARRAY } from '@/shared/lib/constants';
import { Tooltip } from '@/shared/ui/Tooltip';

import { useFleetControlPageContext } from '../../../../model/FleetControlPageContext';
import { FleetControlVehicleMarker } from '../../../FleetControlVehicleMarker';

import styles from './GroupTechnique.module.css';

/**
 * Представляет свойства компонента группы техники.
 */
interface GroupTechniqueProps {
  /** Возвращает заголовок. */
  readonly label: string;
  /** Возвращает иконку. */
  readonly icon: ReactNode;
  /** Возвращает список оборудования. */
  readonly vehicles?: readonly VehicleFleetControl[];
  /** Возвращает признак отображения в рамке. */
  readonly isBordered?: boolean;
  /** Возвращает тип текущего назначенного места. */
  readonly currentAssignedPlace?: AssignPlaceType;
  /** Возвращает идентификатор текущего гаража. */
  readonly currentGarageId?: number;
}

/**
 * Представляет компонент группы техники.
 */
export function GroupTechnique({
  label,
  icon,
  isBordered,
  vehicles,
  currentAssignedPlace,
  currentGarageId,
}: GroupTechniqueProps) {
  const { isOpenSidebar, handleChangeOpenSidebar } = useFleetControlPageContext();

  const { data: statusesData } = useGetAllStatusesQuery();

  const statuses = statusesData?.items ?? EMPTY_ARRAY;

  const [isOpen, setIsOpen] = useState(true);

  const count = vehicles?.length ?? 0;

  if (!isOpenSidebar) {
    return (
      <Tooltip label={label}>
        <div
          className={styles.closest_sidebar_button_container}
          onClick={() => setIsOpen(true)}
        >
          {icon}
        </div>
      </Tooltip>
    );
  }

  return (
    <div className={cn(styles.root, { [styles.bordered]: isBordered })}>
      <div
        className={styles.header}
        onClick={() => setIsOpen(!isOpen)}
      >
        <ArrowIcon
          className={cn(styles.arrow_icon, { [styles.open]: isOpen })}
          onClick={() => handleChangeOpenSidebar(true)}
        />
        {icon}
        <p className={styles.label}>{label}</p>
        <p className={styles.count}>{count}</p>
      </div>
      {isOpen && (
        <div className={styles.vehicles_container}>
          {count > 0
            ? vehicles?.map((vehicle) => (
                <FleetControlVehicleMarker
                  key={vehicle.id}
                  size="s"
                  vehicleId={vehicle.id}
                  vehicleType={vehicle.vehicle_type}
                  name={vehicle.name}
                  color={statuses.find((status) => status.system_name === vehicle.state)?.color}
                  isNormalLabelPosition
                  currentAssignedPlace={currentAssignedPlace}
                  currentGarageId={currentGarageId}
                  iconOpacity={!vehicle.is_assigned ? 0.5 : undefined}
                />
              ))
            : 'Нет данных'}
        </div>
      )}
    </div>
  );
}
