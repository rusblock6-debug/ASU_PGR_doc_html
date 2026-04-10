import { skipToken } from '@reduxjs/toolkit/query';

import { useGetHorizonGraphQuery } from '@/shared/api/endpoints/horizons';
import { useAppSelector } from '@/shared/lib/hooks/useAppSelector';

import { MAP_SCENE } from '../../../config/map-scene';
import { toScene } from '../../../lib/coordinates';
import { tooltipStore } from '../../../lib/tooltip-store';
import {
  selectFormTarget,
  selectHiddenPlaceIds,
  selectMapFocusTarget,
  selectPlacementPlaceToAdd,
  selectSelectedHorizonId,
} from '../../../model/selectors';

import { PlaceMarker } from './PlaceMarker';
import { PlaceTooltip } from './PlaceTooltip';

/**
 * Представляет свойства компонента {@link PlacesLayer}.
 */
interface PlacesLayerProps {
  /** Интерактивны ли маркеры (hover, тултипы). При `false` — pointer events отключены. */
  readonly interactive?: boolean;
}

/**
 * Слой маркеров мест на карте.
 * Отображает точки мест из horizon graph, обрабатывает hover и показывает тултип с координатами и типом.
 */
export function PlacesLayer({ interactive = true }: PlacesLayerProps) {
  const horizonId = useAppSelector(selectSelectedHorizonId);
  const { data } = useGetHorizonGraphQuery(horizonId ?? skipToken);
  const hiddenPlaceIds = useAppSelector(selectHiddenPlaceIds);
  const focusTarget = useAppSelector(selectMapFocusTarget);
  const formTarget = useAppSelector(selectFormTarget);
  const placementPlaceToAdd = useAppSelector(selectPlacementPlaceToAdd);

  if (!data || !data.places?.length) return null;

  const visiblePlaces = data.places.filter(
    (item) => !hiddenPlaceIds.includes(item.id) && !(formTarget?.id === item.id && placementPlaceToAdd?.position),
  );

  const handlePlaceHover = (placeId: number | null) => {
    if (placeId === null) {
      tooltipStore.hide();
      return;
    }

    const place = visiblePlaces.find((place) => place.id === placeId);
    if (!place) return;

    tooltipStore.show(
      <PlaceTooltip
        placeId={place.id}
        placeName={place.name}
        cargoType={place.cargo_type}
      />,
    );
  };

  if (!visiblePlaces.length) return null;

  return (
    <group>
      {visiblePlaces.map((place) => {
        if (!place.location) return null;

        return (
          <PlaceMarker
            key={place.id}
            id={place.id}
            name={place.name}
            placeType={place.type}
            position={toScene(place.location.lon, place.location.lat, MAP_SCENE.PLACES_Y)}
            isSelected={focusTarget?.entity === 'place' && focusTarget.id === place.id}
            interactive={interactive}
            onHover={handlePlaceHover}
          />
        );
      })}
    </group>
  );
}
