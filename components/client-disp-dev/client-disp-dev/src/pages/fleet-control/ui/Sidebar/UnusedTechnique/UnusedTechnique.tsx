import { type FleetControlResponse } from '@/shared/api/endpoints/fleet-control';
import ClockCloseIcon from '@/shared/assets/icons/ic-clock-close.svg?react';
import DockCloseIcon from '@/shared/assets/icons/ic-dock-close.svg?react';
import ParkIcon from '@/shared/assets/icons/ic-park-orange.svg?react';
import { cn } from '@/shared/lib/classnames-utils';
import { EMPTY_ARRAY } from '@/shared/lib/constants';
import { hasValue } from '@/shared/lib/has-value';

import { useFleetControlPageDataSource } from '../../../lib/hooks/useFleetControlPageDataSource';
import { useFleetControlPageContext } from '../../../model/FleetControlPageContext';
import { Divider } from '../../Divider';

import { GroupTechnique } from './GroupTechnique';
import styles from './UnusedTechnique.module.css';

/**
 * Представляет компонент списка неиспользуемой техники.
 */
export function UnusedTechnique() {
  const { isOpenSidebar, handleChangeOpenSidebar } = useFleetControlPageContext();

  const { fleetControlData } = useFleetControlPageDataSource();

  const count = getUnusedTechniqueCount(fleetControlData);

  return (
    <div className={cn(styles.root, { [styles.close]: !isOpenSidebar })}>
      {isOpenSidebar && (
        <div className={styles.header}>
          <p className={styles.title}>Незадействованная техника</p>
          <p className={styles.count}>{count}</p>
        </div>
      )}
      <div className={cn(styles.groups, { [styles.close]: !isOpenSidebar })}>
        <GroupTechnique
          label="В простое"
          vehicles={fleetControlData?.idle ?? EMPTY_ARRAY}
          icon={
            <ClockCloseIcon
              className={styles.grey_icon}
              onClick={() => handleChangeOpenSidebar(true)}
            />
          }
          isBordered
        />
        <GroupTechnique
          label="Нет задания"
          vehicles={fleetControlData?.no_task ?? EMPTY_ARRAY}
          icon={
            <DockCloseIcon
              className={styles.grey_icon}
              onClick={() => handleChangeOpenSidebar(true)}
            />
          }
          currentAssignedPlace="NO_TASK"
        />
        <Divider
          height={1}
          color="var(--bg-widget-hover)"
        />
        {fleetControlData?.garages?.map((garage) => (
          <GroupTechnique
            key={garage.id}
            vehicles={garage.vehicles}
            label={garage.name}
            icon={<ParkIcon onClick={() => handleChangeOpenSidebar(true)} />}
            currentAssignedPlace="GARAGE"
            currentGarageId={garage.id}
          />
        ))}
      </div>
    </div>
  );
}

/**
 * Возвращает общее количество незадействованной техники.
 *
 * @param fleetControlData данные на странице "Управление техникой".
 */
function getUnusedTechniqueCount(fleetControlData?: FleetControlResponse) {
  if (!fleetControlData) {
    return 0;
  }

  const { garages, no_task: noTask, idle } = fleetControlData;

  const garageVehicles = garages?.flatMap((g) => g.vehicles) ?? [];
  const noTaskVehicles = noTask ?? [];
  const idleVehicles = idle ?? [];

  const allVehicles = [...garageVehicles, ...noTaskVehicles, ...idleVehicles].filter(hasValue);

  const vehicleSet = new Set<number>();

  allVehicles.forEach((vehicle) => vehicleSet.add(vehicle.id));

  return vehicleSet.size;
}
