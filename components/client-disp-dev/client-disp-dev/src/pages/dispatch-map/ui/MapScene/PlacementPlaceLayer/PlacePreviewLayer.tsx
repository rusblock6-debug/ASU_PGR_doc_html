import { useFrame } from '@react-three/fiber';
import { useRef } from 'react';
import type { Group } from 'three';

import type { PlacementPlace } from '../../../model/types';
import { useGroundPointerContext } from '../../GroundPointerProvider';
import { PlaceMarker } from '../PlacesLayer/PlaceMarker';

/**
 * Представляет свойства компонента слоя для отображения предварительной позиции иконки места на карте.
 */
interface PlacePreviewLayerProps {
  /** Возвращает место для размещения на карте. */
  readonly placementPlace: PlacementPlace;
}

/**
 * Представляет компонент слоя для отображения предварительной позиции иконки места на карте.
 */
export function PlacePreviewLayer({ placementPlace }: PlacePreviewLayerProps) {
  const ref = useRef<Group>(null);
  const { pointerRef } = useGroundPointerContext();

  useFrame(() => {
    const place = ref.current;
    if (!place) return;

    const { x, y, z } = pointerRef.current;

    if (place.position.x !== x || place.position.y !== y || place.position.z !== z) {
      place.position.set(x, y, z);
    }
  });

  return (
    <PlaceMarker
      ref={ref}
      id={null}
      placeType={placementPlace.placeType}
      position={[0, 0, 0]}
      isPreview
      hint="Нажмите на вершины дороги для привязки"
    />
  );
}
