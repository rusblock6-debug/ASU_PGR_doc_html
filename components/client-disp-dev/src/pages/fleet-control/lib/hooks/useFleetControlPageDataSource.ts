import { useGetFleetControlQuery, useGetFleetControlRoutesQuery } from '@/shared/api/endpoints/fleet-control';
import { useGetAllHorizonsQuery } from '@/shared/api/endpoints/horizons';
import { useGetAllLoadTypeQuery } from '@/shared/api/endpoints/load-types';
import { useGetAllPlacesQuery } from '@/shared/api/endpoints/places';
import { useGetAllSectionsQuery } from '@/shared/api/endpoints/sections';
import { EMPTY_ARRAY } from '@/shared/lib/constants';

import { POLLING_INTERVAL } from '../../model/constants';
import { useFleetControlPageContext } from '../../model/FleetControlPageContext';

/**
 * Хук источника данных для страницы "Управление техникой".
 */
export function useFleetControlPageDataSource() {
  const { routesFilterState } = useFleetControlPageContext();

  const fleetControlQueryArgs =
    routesFilterState.filterState.size > 0 ? { route_id: Array.from(routesFilterState.filterState) } : undefined;

  const { data: fleetControlData, refetch: refetchFleetControlData } = useGetFleetControlQuery(fleetControlQueryArgs, {
    refetchOnMountOrArgChange: true,
    pollingInterval: POLLING_INTERVAL.RARELY,
  });

  const { data: fleetControlRoutesData } = useGetFleetControlRoutesQuery(undefined, {
    pollingInterval: POLLING_INTERVAL.RARELY,
  });

  const { data: placesData } = useGetAllPlacesQuery(undefined, {
    pollingInterval: POLLING_INTERVAL.OFTEN,
  });

  const places = placesData?.items?.length ? placesData.items : EMPTY_ARRAY;

  const { data: sectionsData } = useGetAllSectionsQuery(undefined, {
    pollingInterval: POLLING_INTERVAL.OFTEN,
  });

  const sections = sectionsData?.items?.length ? sectionsData.items : EMPTY_ARRAY;

  const { data: cargoData } = useGetAllLoadTypeQuery();

  const { data: horizonsData } = useGetAllHorizonsQuery();

  return {
    fleetControlData,
    refetchFleetControlData,
    fleetControlRoutesData,
    places,
    sections,
    cargoData,
    horizonsData,
  };
}
