import type { PlacementPlace } from '../../../model/types';
import { PlaceMarker } from '../PlacesLayer/PlaceMarker';

/**
 * Представляет свойства компонента слоя для отображения новой позиции иконки места на карте.
 */
interface PlacementObjectsLayerProps {
  /** Возвращает место для размещения на карте. */
  readonly placementPlace: PlacementPlace;
}

/**
 * Представляет компонент слоя для отображения новой позиции иконки места на карте.
 */
export function PlacementObjectsLayer({ placementPlace }: PlacementObjectsLayerProps) {
  if (!placementPlace.position) return null;

  return (
    <PlaceMarker
      id={null}
      placeType={placementPlace.placeType}
      position={placementPlace.position}
      isPreview
    />
  );
}
