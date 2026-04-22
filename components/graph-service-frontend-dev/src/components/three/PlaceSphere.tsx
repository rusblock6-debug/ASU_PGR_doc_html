/**
 * Компонент для отрисовки места (place) в 3D
 */
import React from 'react';
import { Billboard, Sphere, Text } from '@react-three/drei';
import { Place } from '../../types/graph';
import { getPlaceCanvasXY, TransformGPStoCanvas } from '../../utils/placeLocation';

interface PlaceSphereProps {
  place: Place;
  height?: number;
  radius?: number;
  transformGPStoCanvas: TransformGPStoCanvas;
}

export const PlaceSphere = React.memo(function PlaceSphere({ place, height, radius, transformGPStoCanvas }: PlaceSphereProps) {
  const xy = React.useMemo(() => getPlaceCanvasXY(place, transformGPStoCanvas), [place, transformGPStoCanvas]);
  if (!xy) return null;

  return (
    <group position={[xy.x, height ?? place.horizon?.height ?? 0, -xy.y]}>
      {radius && radius > 0 && (
        <Sphere args={[radius, 16, 16]} renderOrder={0}>
          <meshBasicMaterial color="#FF6600" transparent opacity={0.08} depthWrite={false} />
        </Sphere>
      )}
      <Sphere args={[2.2, 16, 16]}>
        <meshStandardMaterial color="#FF6600" emissive="#FF8844" emissiveIntensity={0.7} />
      </Sphere>

      <Billboard position={[0, 10, 0]} follow>
        <Text
          fontSize={3.6}
          color="#FEFCF9"
          anchorX="center"
          anchorY="middle"
          outlineWidth={0.5}
          outlineColor="#000000"
        >
          {place.name}
        </Text>
      </Billboard>
    </group>
  );
});



