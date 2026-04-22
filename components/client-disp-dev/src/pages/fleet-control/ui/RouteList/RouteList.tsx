import { type DragEndEvent, useDndMonitor } from '@dnd-kit/core';
import { arrayMove, rectSortingStrategy, SortableContext, verticalListSortingStrategy } from '@dnd-kit/sortable';
import { useEffect, useState } from 'react';

import { type RouteFleetControl } from '@/shared/api/endpoints/fleet-control';
import { assertHasValue } from '@/shared/lib/assert-has-value';
import { cn } from '@/shared/lib/classnames-utils';
import { hasValue } from '@/shared/lib/has-value';

import { useAssignmentVehicle } from '../../lib/hooks/useAssignmentVehicle';
import { useFleetControlPageDataSource } from '../../lib/hooks/useFleetControlPageDataSource';
import { FLEET_CONTROL_MODE } from '../../model/fleet-control-mode';
import { useFleetControlPageContext } from '../../model/FleetControlPageContext';
import { isVehicleDragData } from '../../model/vehicle-drag-data';
import { isVehicleDropData } from '../../model/vehicle-drop-data';

import { RouteItem } from './RouteItem';
import styles from './RouteList.module.css';

/** Ключ для сохранения порядка отображения маршрутов в локальном хранилище. */
const STORAGE_KEY = 'asu-gtk-fleet-control-route-order';

/**
 * Представляет компонент списка маршрутов.
 */
export function RouteList() {
  const { fleetControlMode, isAddNewRoute, draggableElement, handleChangeDraggableElement } =
    useFleetControlPageContext();

  const { fleetControlData } = useFleetControlPageDataSource();

  const isHorizontalMode = fleetControlMode === FLEET_CONTROL_MODE.HORIZONTAL;

  const routes = fleetControlData?.routes;

  const [sortableItems, setSortableItems] = useState<readonly RouteFleetControl[]>([]);

  useEffect(() => {
    if (!routes) return;

    const saved = localStorage.getItem(STORAGE_KEY);

    if (!hasValue(saved)) {
      setSortableItems(routes);
      setLocalStorageOrderRoutes(routes);
      return;
    }

    let savedIds: string[] = [];

    try {
      savedIds = JSON.parse(saved) as string[];
    } catch {
      setSortableItems(routes);
      setLocalStorageOrderRoutes(routes);
      return;
    }

    const map = new Map(routes.map((route) => [route.route_id, route]));

    const ordered = savedIds.map((id) => map.get(id)).filter(hasValue);

    const savedSet = new Set(savedIds);
    const newItems = routes.filter((route) => !savedSet.has(route.route_id));

    const finalItems = [...newItems, ...ordered];

    setSortableItems(finalItems);
    setLocalStorageOrderRoutes(finalItems);
  }, [routes]);

  const handleAssignment = useAssignmentVehicle();

  const onDragStart = (event: DragEndEvent) => {
    const { active } = event;

    const activeData = active?.data.current;

    if (typeof active.id === 'string' && isVehicleDragData(activeData)) {
      const { vehicleId, vehicleName, vehicleType, vehicleColor } = activeData;
      handleChangeDraggableElement({
        id: active.id,
        elementType: 'vehicle',
        vehicleId,
        vehicleName,
        vehicleType,
        vehicleColor,
      });
      return;
    }

    if (typeof active.id === 'string') {
      handleChangeDraggableElement({ id: active.id, elementType: 'route' });
    }
  };

  const onDragEnd = async (event: DragEndEvent) => {
    const { active, over } = event;

    const activeData = active?.data.current;
    const overData = over?.data.current;

    if (isVehicleDragData(activeData) && isVehicleDropData(overData)) {
      const {
        vehicleId,
        vehicleName,
        currentAssignedPlace,
        currentGarageId,
        currentRoutePlaceAId,
        currentRoutePlaceBId,
      } = activeData;

      const { targetKind, targetGarageId, targetRoutePlaceAId, targetRoutePlaceBId } = overData;

      assertHasValue(currentAssignedPlace);

      try {
        await handleAssignment({
          vehicleId,
          vehicleName,
          currentAssignedPlace,
          currentRoutePlaceAId,
          currentRoutePlaceBId,
          currentGarageId,
          targetKind,
          targetGarageId,
          targetRoutePlaceAId,
          targetRoutePlaceBId,
        });
      } finally {
        handleChangeDraggableElement(null);
      }
      return;
    }

    if (over && active.id !== over.id) {
      setSortableItems((items) => {
        const oldIndex = items.findIndex((item) => item.route_id === active.id);
        const newIndex = items.findIndex((item) => item.route_id === over.id);

        if (oldIndex === -1 || newIndex === -1) return items;

        const newOrder = arrayMove([...items], oldIndex, newIndex);

        setLocalStorageOrderRoutes(newOrder);

        return newOrder;
      });

      handleChangeDraggableElement(null);
    }
  };

  useDndMonitor({
    onDragStart,
    onDragEnd,
  });

  return (
    <div
      className={cn(styles.root, { [styles.horizontal]: isHorizontalMode }, { [styles.vertical]: !isHorizontalMode })}
    >
      {sortableItems.length > 0 || isAddNewRoute ? (
        <div className={styles.items_container}>
          {isAddNewRoute && (
            <RouteItem
              route={{ route_id: 'DRAFT_ROUTE' }}
              isFirst
              isLast={sortableItems.length === 0}
              canDrag={false}
            />
          )}
          <SortableContext
            items={sortableItems.map((item) => item.route_id)}
            strategy={isHorizontalMode ? verticalListSortingStrategy : rectSortingStrategy}
          >
            {sortableItems.map((item, index, array) => (
              <RouteItem
                key={item.route_id}
                route={item}
                isDragging={draggableElement?.id === item.route_id}
                isFirst={index === 0}
                isLast={index === array.length - 1}
              />
            ))}
          </SortableContext>
        </div>
      ) : (
        <div className={styles.no_data}>Нет данных</div>
      )}
    </div>
  );
}

/**
 * Сохраняет порядок маршрутов в local storage.
 *
 * @param routes список маршрутов.
 */
function setLocalStorageOrderRoutes(routes: readonly RouteFleetControl[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(routes.map((route) => route.route_id)));
}
