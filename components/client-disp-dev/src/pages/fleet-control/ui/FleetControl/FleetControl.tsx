import {
  DndContext,
  DragOverlay,
  KeyboardSensor,
  PointerSensor,
  rectIntersection,
  useSensor,
  useSensors,
} from '@dnd-kit/core';
import { restrictToParentElement, restrictToVerticalAxis } from '@dnd-kit/modifiers';
import { sortableKeyboardCoordinates } from '@dnd-kit/sortable';

import { hasValue } from '@/shared/lib/has-value';

import { useFleetControlPageDataSource } from '../../lib/hooks/useFleetControlPageDataSource';
import { isDraggableRoute, isDraggableVehicle } from '../../model/draggable-element';
import { FLEET_CONTROL_MODE } from '../../model/fleet-control-mode';
import { useFleetControlPageContext } from '../../model/FleetControlPageContext';
import { FleetControlVehicleMarker } from '../FleetControlVehicleMarker';
import { MoveVehicleOnRouteModal } from '../MoveVehicleOnRouteModal';
import { RouteList } from '../RouteList';
import { RouteItem } from '../RouteList/RouteItem';
import { Sidebar } from '../Sidebar';

import styles from './FleetControl.module.css';

/**
 * Представляет компонент для управления техникой.
 */
export function FleetControl() {
  const { fleetControlMode, movingVehicle, draggableElement } = useFleetControlPageContext();

  const isRouteMoving = hasValue(draggableElement) && isDraggableRoute(draggableElement);

  const { fleetControlData } = useFleetControlPageDataSource();

  const routes = fleetControlData?.routes;

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: 1 },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    }),
  );

  const modifiers =
    fleetControlMode === FLEET_CONTROL_MODE.HORIZONTAL
      ? [restrictToParentElement, restrictToVerticalAxis]
      : [restrictToParentElement];

  const draggableRoute = routes?.find((item) => item.route_id === draggableElement?.id);

  return (
    <div className={styles.root}>
      <DndContext
        sensors={sensors}
        collisionDetection={rectIntersection}
        modifiers={isRouteMoving ? modifiers : undefined}
      >
        <RouteList />
        <Sidebar />
        <DragOverlay>
          {draggableRoute && (
            <RouteItem
              route={draggableRoute}
              isDragged
            />
          )}
          {isDraggableVehicle(draggableElement) && (
            <FleetControlVehicleMarker
              vehicleId={draggableElement.vehicleId}
              name={draggableElement.vehicleName}
              vehicleType={draggableElement.vehicleType}
              color={draggableElement.vehicleColor}
            />
          )}
        </DragOverlay>
      </DndContext>
      {hasValue(movingVehicle) && <MoveVehicleOnRouteModal movingVehicle={movingVehicle} />}
    </div>
  );
}
