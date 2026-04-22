import { useDraggable } from '@dnd-kit/core';

import type { VehicleDragData } from '../../model/vehicle-drag-data';
import { FleetControlVehicleMarker, type FleetControlVehicleMarkerProps } from '../FleetControlVehicleMarker';

/**
 * Представляет компонент-обертку для реализации перемещения техники при помощи drag and drop.
 */
export function DraggableFleetControlVehicleMarker({ vehicleId, ...props }: Readonly<FleetControlVehicleMarkerProps>) {
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({
    id: `vehicle-${vehicleId}`,
    data: {
      moveType: 'vehicle-drag',
      vehicleId,
      vehicleType: props.vehicleType,
      vehicleName: props.name,
      vehicleColor: props.color,
      currentAssignedPlace: props.currentAssignedPlace,
      currentGarageId: props.currentGarageId ?? null,
      currentRoutePlaceAId: props.currentRoutePlaceAId ?? null,
      currentRoutePlaceBId: props.currentRoutePlaceBId ?? null,
    } satisfies VehicleDragData,
  });

  const style = {
    opacity: isDragging ? 0.5 : 1,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...listeners}
      {...attributes}
    >
      <FleetControlVehicleMarker
        vehicleId={vehicleId}
        {...props}
      />
    </div>
  );
}
