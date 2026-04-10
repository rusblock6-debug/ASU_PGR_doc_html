import {
  type RouteDraftFleetControl,
  type RouteFleetControl,
  useGetFleetControlRoutesStreamQuery,
} from '@/shared/api/endpoints/fleet-control';
import { useGetAllStatusesQuery } from '@/shared/api/endpoints/statuses';
import { cn } from '@/shared/lib/classnames-utils';
import { EMPTY_ARRAY } from '@/shared/lib/constants';
import { hasValue } from '@/shared/lib/has-value';

import { FleetControlVehicleMarker } from '../../../../FleetControlVehicleMarker';

import styles from './RouteVehicles.module.css';

/**
 * Представляет свойства компонента для отображения техники на маршруте.
 */
interface RouteVehiclesProps {
  /** Возвращает маршрут. */
  readonly route: RouteFleetControl | RouteDraftFleetControl;
  /** Возвращает признак горизонтального режима отображения маршрутов. */
  readonly isHorizontalMode: boolean;
}

/**
 * Представляет компонент для отображения техники на маршруте.
 */
export function RouteVehicles({ route, isHorizontalMode }: RouteVehiclesProps) {
  const { data: routesStreamData } = useGetFleetControlRoutesStreamQuery();

  const { data: statusesData } = useGetAllStatusesQuery();

  const statuses = statusesData?.items ?? EMPTY_ARRAY;

  return (
    <div
      className={cn(
        styles.vehicles_on_route_container,
        { [styles.horizontal]: isHorizontalMode },
        { [styles.vertical]: !isHorizontalMode },
      )}
    >
      {route.vehicles?.map((vehicle) => {
        const vehicleStreamData = routesStreamData?.find((item) => item.vehicle_id === vehicle.id);
        const progressPercent = vehicleStreamData?.progress_percent ?? 50;
        const isMovingForward = vehicleStreamData?.is_moving_forward ?? false;
        const state = vehicleStreamData?.state;

        const currentState = hasValue(state) ? state : vehicle.state;

        return (
          <div
            key={vehicle.id}
            className={cn(styles.vehicle_marker_container, { [styles.horizontal]: isHorizontalMode })}
            style={{
              left: isHorizontalMode ? `clamp(35px, ${progressPercent}%, calc(100% - 35px))` : undefined,
              top: !isHorizontalMode ? `clamp(2px, ${progressPercent}%, calc(100% - 20px))` : undefined,
            }}
          >
            <FleetControlVehicleMarker
              vehicleId={vehicle.id}
              vehicleType={vehicle.vehicle_type}
              name={vehicle.name}
              color={statuses.find((status) => status.system_name === currentState)?.color}
              horizontal={!isHorizontalMode}
              currentAssignedPlace="ROUTE"
              currentRoutePlaceAId={route.place_a_id}
              currentRoutePlaceBId={route.place_b_id}
              mirrored={isHorizontalMode && isMovingForward}
              iconOpacity={!vehicle.is_assigned ? 0.5 : undefined}
            />
          </div>
        );
      })}
    </div>
  );
}
