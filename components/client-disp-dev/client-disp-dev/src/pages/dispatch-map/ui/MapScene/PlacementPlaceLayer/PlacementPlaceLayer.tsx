import { useAppSelector } from '@/shared/lib/hooks/useAppSelector';

import { selectPlacementPlaceToAdd } from '../../../model/selectors';

import { NodeSelectorLayer } from './NodeSelectorLayer';
import { PlacementObjectsLayer } from './PlacementObjectsLayer';
import { PlacePreviewLayer } from './PlacePreviewLayer';

/**
 * Представляет компонент слоя для размещения мест на карте.
 */
export function PlacementPlaceLayer() {
  const placementPlaceToAdd = useAppSelector(selectPlacementPlaceToAdd);

  if (!placementPlaceToAdd) {
    return null;
  }

  return (
    <>
      {placementPlaceToAdd.isPlacementMode && (
        <>
          <NodeSelectorLayer placementPlace={placementPlaceToAdd} />
          <PlacePreviewLayer placementPlace={placementPlaceToAdd} />
        </>
      )}

      <PlacementObjectsLayer placementPlace={placementPlaceToAdd} />
    </>
  );
}
