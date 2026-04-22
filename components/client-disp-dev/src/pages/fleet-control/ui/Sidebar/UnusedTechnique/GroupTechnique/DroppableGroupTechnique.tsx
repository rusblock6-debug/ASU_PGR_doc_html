import { useDroppable } from '@dnd-kit/core';

import type { AssignPlaceType } from '@/shared/api/endpoints/fleet-control';

import type { VehicleDropData } from '../../../../model/vehicle-drop-data';

import { GroupTechnique, type GroupTechniqueProps } from './GroupTechnique';

/**
 * Представляет свойства компонента-обертки для компонента {@link GroupTechnique} для перемещения оборудования.
 */
interface DroppableGroupTechniqueProps extends Omit<GroupTechniqueProps, 'currentAssignedPlace'> {
  /** Возвращает тип места назначения. */
  readonly currentAssignedPlace: AssignPlaceType;
}

/**
 * Представляет компонент-обертку для компонента {@link GroupTechnique} для перемещения оборудования.
 */
export function DroppableGroupTechnique(props: DroppableGroupTechniqueProps) {
  const { setNodeRef, isOver } = useDroppable({
    id: `${props.currentAssignedPlace}-${props.currentGarageId}`,
    data: {
      moveType: 'vehicle-drop',
      targetKind: props.currentAssignedPlace,
      targetGarageId: props.currentGarageId,
    } satisfies VehicleDropData,
  });

  return (
    <GroupTechnique
      ref={setNodeRef}
      isDropHovered={isOver}
      {...props}
    />
  );
}
