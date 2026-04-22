import type { MenuProps } from '@mantine/core';
import { useMemo, useState } from 'react';

import { cn } from '@/shared/lib/classnames-utils';
import { EMPTY_ARRAY } from '@/shared/lib/constants';
import { Menu } from '@/shared/ui/Menu';
import { MenuTargetButton } from '@/shared/ui/MenuTargetButton';

import { useFleetControlPageDataSource } from '../../lib/hooks/useFleetControlPageDataSource';
import { useFleetControlPageContext } from '../../model/FleetControlPageContext';

import styles from './RouteFilter.module.css';
import { type RouteFilterItem, RouteFilterList } from './RouteFilterList';

/**
 * Представляет компонент фильтра по транспортным средствам.
 */
export function RouteFilter({ withinPortal }: Readonly<Pick<MenuProps, 'withinPortal'>>) {
  const {
    routesFilterState: { filterState, onAddRoutesFromFilter, onRemoveRoutesFromFilter },
  } = useFleetControlPageContext();

  const { fleetControlRoutesData, sections, places } = useFleetControlPageDataSource();

  const placesMap = useMemo(() => new Map(places.map((place) => [place.id, place])), [places]);

  const groupedRoutesBySection = sections.map((section) => ({
    id: section.id,
    name: section.name,
    routes: fleetControlRoutesData
      ?.filter((route) => {
        const placeA = placesMap.get(route.place_a_id);
        const placeB = placesMap.get(route.place_b_id);

        return placeA?.section_ids.includes(section.id) || placeB?.section_ids.includes(section.id);
      })
      .map(
        (r) =>
          ({
            route_id: r.route_id,
            place_a_name: placesMap.get(r.place_a_id)?.name ?? '',
            place_b_name: placesMap.get(r.place_b_id)?.name ?? '',
          }) satisfies RouteFilterItem,
      ),
  }));

  const [opened, setOpened] = useState(false);

  const selectedRoutesCount = filterState.size;

  return (
    <Menu
      onChange={setOpened}
      closeOnClickOutside
      width="target"
      withinPortal={withinPortal}
    >
      <Menu.Target>
        <div>
          <MenuTargetButton
            opened={opened}
            label="Маршруты на странице"
            afterLabel={
              <div className={cn(styles.count_container, { [styles.empty]: selectedRoutesCount === 0 })}>
                {selectedRoutesCount > 0 && <p>{selectedRoutesCount}</p>}
              </div>
            }
          />
        </div>
      </Menu.Target>

      <Menu.Dropdown>
        {groupedRoutesBySection.map((section) => (
          <RouteFilterList
            key={section.id}
            sectionName={section.name}
            routes={section.routes ?? EMPTY_ARRAY}
            selectedRouteIds={filterState}
            onAddRoutesFromFilter={onAddRoutesFromFilter}
            onRemoveRoutesFromFilter={onRemoveRoutesFromFilter}
          />
        ))}
      </Menu.Dropdown>
    </Menu>
  );
}
