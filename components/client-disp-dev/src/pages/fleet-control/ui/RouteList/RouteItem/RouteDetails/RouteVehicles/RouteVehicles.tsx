import { useDroppable } from '@dnd-kit/core';

import {
  type RouteDraftFleetControl,
  type RouteFleetControl,
  useGetFleetControlRoutesStreamQuery,
  type VehicleFleetControl,
} from '@/shared/api/endpoints/fleet-control';
import { useGetAllStatusesQuery } from '@/shared/api/endpoints/statuses';
import { assertHasValue } from '@/shared/lib/assert-has-value';
import { cn } from '@/shared/lib/classnames-utils';
import { EMPTY_ARRAY } from '@/shared/lib/constants';
import { hasValue } from '@/shared/lib/has-value';

import type { VehicleDropData } from '../../../../../model/vehicle-drop-data';
import { DraggableFleetControlVehicleMarker } from '../../../../DraggableFleetControlVehicleMarker';

import styles from './RouteVehicles.module.css';

/**
 * Представляет оборудование на маршруте.
 */
interface VehicleOnRoute extends VehicleFleetControl {
  /** Возвращает признак, что оборудование движется вперед (к месту разгрузки). */
  readonly isMovingForward: boolean;
  /** Возвращает процент завершения маршрута. */
  readonly progressPercent?: number;
  /** Возвращает признак груженого оборудования. */
  readonly isLoaded: boolean;
}

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
  const { setNodeRef, isOver } = useDroppable({
    id: `ROUTE-${route.route_id}`,
    data: {
      moveType: 'vehicle-drop',
      targetKind: 'ROUTE',
      targetRoutePlaceAId: route.place_a_id,
      targetRoutePlaceBId: route.place_b_id,
    } satisfies VehicleDropData,
    disabled: route.route_id === 'DRAFT_ROUTE',
  });

  const { data: routesStreamData } = useGetFleetControlRoutesStreamQuery();

  const { data: statusesData } = useGetAllStatusesQuery();

  const statuses = statusesData?.items ?? EMPTY_ARRAY;

  const routeVehicles = route.vehicles?.map<VehicleOnRoute>((vehicle) => {
    const vehicleStreamData = routesStreamData?.find((item) => item.vehicle_id === vehicle.id);
    const progressPercent = vehicleStreamData?.progress_percent;
    const isMovingForward = vehicleStreamData?.is_moving_forward ?? false;
    const isLoaded = vehicleStreamData?.is_loaded ?? false;
    const state = vehicleStreamData?.state;

    const currentState = hasValue(state) ? state : vehicle.state;

    return {
      ...vehicle,
      state: currentState,
      progressPercent,
      isMovingForward,
      isLoaded,
    } satisfies VehicleOnRoute;
  });

  const vehiclesForVerticalMode = (() => {
    const empty = routeVehicles
      ?.filter((item) => item.is_assigned && hasValue(item.progressPercent) && !item.isLoaded)
      .sort(vehiclesSortComparator);

    const notAssigned = routeVehicles?.filter((item) => !item.is_assigned);

    const loaded = routeVehicles
      ?.filter((item) => item.is_assigned && hasValue(item.progressPercent) && item.isLoaded)
      .sort(vehiclesSortComparator);

    return {
      loaded,
      notAssigned,
      empty,
    };
  })();

  return (
    <div
      ref={setNodeRef}
      className={cn(
        styles.vehicles_on_route_container,
        { [styles.horizontal]: isHorizontalMode },
        { [styles.vertical]: !isHorizontalMode },
        { [styles.drop_hovered]: isOver },
      )}
    >
      {isHorizontalMode ? (
        routeVehicles?.map((vehicle) => (
          <div
            key={vehicle.id}
            className={styles.vehicle_marker_container}
            style={{
              left: `clamp(35px, ${vehicle.progressPercent ?? 50}%, calc(100% - 35px))`,
            }}
          >
            <DraggableFleetControlVehicleMarker
              vehicleId={vehicle.id}
              vehicleType={vehicle.vehicle_type}
              name={vehicle.name}
              color={statuses.find((status) => status.system_name === vehicle.state)?.color}
              currentAssignedPlace="ROUTE"
              currentRoutePlaceAId={route.place_a_id}
              currentRoutePlaceBId={route.place_b_id}
              mirrored={vehicle.isMovingForward}
              iconOpacity={!vehicle.is_assigned ? 0.5 : undefined}
            />
          </div>
        ))
      ) : (
        <div className={styles.vehicles_vertical_root}>
          <div className={cn(styles.vehicles_vertical_container, styles.empty_vehicles)}>
            {vehiclesForVerticalMode.empty?.map((vehicle) => (
              <DraggableFleetControlVehicleMarker
                key={vehicle.id}
                vehicleId={vehicle.id}
                vehicleType={vehicle.vehicle_type}
                name={vehicle.name}
                color={statuses.find((status) => status.system_name === vehicle.state)?.color}
                horizontal
                currentAssignedPlace="ROUTE"
                currentRoutePlaceAId={route.place_a_id}
                currentRoutePlaceBId={route.place_b_id}
                iconOpacity={!vehicle.is_assigned ? 0.5 : undefined}
              />
            ))}
          </div>
          <div className={styles.vehicles_vertical_container}>
            {vehiclesForVerticalMode.notAssigned?.map((vehicle) => (
              <DraggableFleetControlVehicleMarker
                key={vehicle.id}
                vehicleId={vehicle.id}
                vehicleType={vehicle.vehicle_type}
                name={vehicle.name}
                color={statuses.find((status) => status.system_name === vehicle.state)?.color}
                horizontal
                currentAssignedPlace="ROUTE"
                currentRoutePlaceAId={route.place_a_id}
                currentRoutePlaceBId={route.place_b_id}
                iconOpacity={!vehicle.is_assigned ? 0.5 : undefined}
              />
            ))}
          </div>
          <div className={cn(styles.vehicles_vertical_container, styles.loaded_vehicles)}>
            {vehiclesForVerticalMode.loaded?.map((vehicle) => (
              <DraggableFleetControlVehicleMarker
                key={vehicle.id}
                vehicleId={vehicle.id}
                vehicleType={vehicle.vehicle_type}
                name={vehicle.name}
                color={statuses.find((status) => status.system_name === vehicle.state)?.color}
                horizontal
                currentAssignedPlace="ROUTE"
                currentRoutePlaceAId={route.place_a_id}
                currentRoutePlaceBId={route.place_b_id}
                mirrored
                iconOpacity={!vehicle.is_assigned ? 0.5 : undefined}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * Функция сортировки списка оборудования.
 */
function vehiclesSortComparator(a: VehicleOnRoute, b: VehicleOnRoute) {
  assertHasValue(a.progressPercent);
  assertHasValue(b.progressPercent);
  return a.progressPercent - b.progressPercent;
}
