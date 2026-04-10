import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  DragOverlay,
  useSensor,
  useSensors,
  type DragEndEvent,
} from '@dnd-kit/core';
import { restrictToParentElement, restrictToVerticalAxis } from '@dnd-kit/modifiers';
import {
  arrayMove,
  rectSortingStrategy,
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable';
import { useEffect, useState } from 'react';

import { type RouteFleetControl } from '@/shared/api/endpoints/fleet-control';
import { cn } from '@/shared/lib/classnames-utils';
import { hasValue } from '@/shared/lib/has-value';

import { useFleetControlPageDataSource } from '../../lib/hooks/useFleetControlPageDataSource';
import { FLEET_CONTROL_MODE } from '../../lib/types/fleet-conntrol-mode';
import { useFleetControlPageContext } from '../../model/FleetControlPageContext';

import { RouteItem } from './RouteItem';
import styles from './RouteList.module.css';

/** Ключ для сохранения порядка отображения маршрутов в локальном хранилище. */
const STORAGE_KEY = 'asu-gtk-fleet-control-route-order';

/**
 * Представляет компонент списка маршрутов.
 */
export function RouteList() {
  const { fleetControlMode, isAddNewRoute } = useFleetControlPageContext();

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

  const [activeId, setActiveId] = useState<string | null>(null);

  const activeItem = sortableItems.find((item) => item.route_id === activeId);

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    }),
  );

  const onDragStart = (event: DragEndEvent) => {
    setActiveId(String(event.active.id));
  };

  const onDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;

    if (over && active.id !== over.id) {
      setSortableItems((items) => {
        const oldIndex = items.findIndex((item) => item.route_id === active.id);
        const newIndex = items.findIndex((item) => item.route_id === over.id);

        if (oldIndex === -1 || newIndex === -1) return items;

        const newOrder = arrayMove([...items], oldIndex, newIndex);

        setLocalStorageOrderRoutes(newOrder);

        return newOrder;
      });
    }

    setActiveId(null);
  };

  const modifiers = isHorizontalMode ? [restrictToParentElement, restrictToVerticalAxis] : [restrictToParentElement];

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
          <DndContext
            sensors={sensors}
            collisionDetection={closestCenter}
            onDragStart={onDragStart}
            onDragEnd={onDragEnd}
            modifiers={modifiers}
          >
            <SortableContext
              items={sortableItems.map((item) => item.route_id)}
              strategy={isHorizontalMode ? verticalListSortingStrategy : rectSortingStrategy}
            >
              {sortableItems.map((item, index, array) => (
                <RouteItem
                  key={item.route_id}
                  route={item}
                  isDragging={activeId === item.route_id}
                  isFirst={index === 0}
                  isLast={index === array.length - 1}
                />
              ))}
              <DragOverlay>
                {activeItem ? (
                  <RouteItem
                    route={activeItem}
                    isDragged
                  />
                ) : null}
              </DragOverlay>
            </SortableContext>
          </DndContext>
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
