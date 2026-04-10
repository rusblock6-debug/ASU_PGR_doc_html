import { OrbitControls } from '@react-three/drei';
import { Canvas } from '@react-three/fiber';
import type { PointerEvent } from 'react';
import { MOUSE } from 'three';
import type { OrbitControls as OrbitControlsImpl } from 'three-stdlib';

import { useAppSelector } from '@/shared/lib/hooks/useAppSelector';

import { MAP_SCENE, NORTH_AZIMUTH } from '../../config/map-scene';
import { useMapDataLoading } from '../../lib/hooks/useMapDataLoading';
import {
  selectIsGraphEditActive,
  selectIsRulerActive,
  selectMapLayers,
  selectPlacementPlaceToAdd,
} from '../../model/selectors';
import { MapLayer } from '../../model/types';
import { useMapCameraContext } from '../MapCameraProvider';

import { BackgroundLayer } from './BackgroundLayer';
import { CameraController } from './CameraController';
import { GroundPointerTracker } from './GroundPointerTracker';
import { MapLoader } from './MapLoader';
import styles from './MapScene.module.css';
import { PlacementPlaceLayer } from './PlacementPlaceLayer';
import { PlacesLayer } from './PlacesLayer';
import { RoadGraphEditLayer, RoadGraphLayer } from './RoadGraphLayer';
import { RulerLayer } from './RulerLayer';
import { type VehicleData, VehiclesLayer } from './VehiclesLayer';

/**
 * Представляет свойства компонента {@link MapScene}.
 */
interface MapSceneProps {
  /** Транспорт. */
  readonly vehicles?: Record<string, VehicleData>;
}

/**
 * Сцена карты с местами, транспортом и дорожным графом.
 */
export function MapScene({ vehicles }: MapSceneProps) {
  const { controlsRef, compassRef } = useMapCameraContext();
  const isLoading = useMapDataLoading();

  const layers = useAppSelector(selectMapLayers);
  const isGraphEditActive = useAppSelector(selectIsGraphEditActive);
  const isRulerActive = useAppSelector(selectIsRulerActive);
  const placementPlaceToAdd = useAppSelector(selectPlacementPlaceToAdd);

  const isPlacementMode = !!placementPlaceToAdd?.isPlacementMode;
  const isInteractive = !isRulerActive && !isGraphEditActive && !isPlacementMode;

  const getIdleCursor = () => {
    if (isPlacementMode) return 'none';
    if (isRulerActive || isGraphEditActive) return 'pointer';
    return 'grab';
  };

  const getActiveCursor = (event: PointerEvent) => {
    if (event.button === (MOUSE.MIDDLE as number) || event.ctrlKey) return 'move';
    if (isPlacementMode) return 'none';
    if (isRulerActive || isGraphEditActive) return 'pointer';
    return 'grabbing';
  };

  const idleCursor = getIdleCursor();

  const setCanvasCursor = (target: EventTarget, cursor: string) => {
    (target as HTMLElement).style.cursor = cursor;
  };

  const handleControlsChange = (event?: { target: OrbitControlsImpl }) => {
    if (event?.target && compassRef.current) {
      compassRef.current.style.rotate = `${-(event.target.getAzimuthalAngle() - NORTH_AZIMUTH)}rad`;
    }
  };

  if (isLoading) return <MapLoader />;

  const ActiveRoadGraphLayer = isGraphEditActive ? RoadGraphEditLayer : RoadGraphLayer;

  return (
    <Canvas
      className={styles.canvas}
      style={{ cursor: idleCursor }}
      gl={{ logarithmicDepthBuffer: true }}
      camera={{
        position: MAP_SCENE.CAMERA.INITIAL_POSITION,
        fov: MAP_SCENE.CAMERA.FOV,
        near: MAP_SCENE.CAMERA.NEAR,
        far: MAP_SCENE.CAMERA.FAR,
      }}
      onPointerDown={(event) => setCanvasCursor(event.target, getActiveCursor(event))}
      onPointerUp={(event) => setCanvasCursor(event.target, idleCursor)}
    >
      <ambientLight intensity={0.7} />
      <directionalLight
        position={[500, 1200, 300]}
        intensity={0.8}
      />
      <directionalLight
        position={[-300, 900, -200]}
        intensity={0.3}
      />

      <OrbitControls
        ref={controlsRef}
        onChange={handleControlsChange}
        enableRotate
        enablePan
        enableZoom
        mouseButtons={{
          LEFT: MOUSE.PAN,
          MIDDLE: MOUSE.ROTATE,
        }}
        screenSpacePanning={false}
        minPolarAngle={0.1}
        maxPolarAngle={Math.PI / 3}
        maxDistance={MAP_SCENE.CAMERA_MAX_DISTANCE}
        minDistance={MAP_SCENE.CAMERA_MIN_DISTANCE}
        enableDamping
        dampingFactor={0.1}
      />

      <CameraController vehicles={vehicles} />

      <GroundPointerTracker />

      {layers[MapLayer.BACKGROUND] && <BackgroundLayer />}

      <PlacesLayer interactive={isInteractive} />

      {(layers[MapLayer.ROADS] || isPlacementMode) && <ActiveRoadGraphLayer />}

      {vehicles && (
        <VehiclesLayer
          vehicles={vehicles}
          interactive={isInteractive}
        />
      )}

      {isRulerActive && <RulerLayer />}

      <PlacementPlaceLayer />
    </Canvas>
  );
}
