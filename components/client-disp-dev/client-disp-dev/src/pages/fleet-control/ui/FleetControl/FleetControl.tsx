import { hasValue } from '@/shared/lib/has-value';

import { useFleetControlPageContext } from '../../model/FleetControlPageContext';
import { MoveVehicleOnRouteModal } from '../MoveVehicleOnRouteModal';
import { RouteList } from '../RouteList';
import { Sidebar } from '../Sidebar';

import styles from './FleetControl.module.css';

/**
 * Представляет компонент для управления техникой.
 */
export function FleetControl() {
  const { movingVehicle } = useFleetControlPageContext();

  return (
    <div className={styles.root}>
      <RouteList />
      <Sidebar />
      {hasValue(movingVehicle) && <MoveVehicleOnRouteModal movingVehicle={movingVehicle} />}
    </div>
  );
}
