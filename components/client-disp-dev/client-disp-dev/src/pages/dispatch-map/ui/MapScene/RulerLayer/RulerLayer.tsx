import { MAP_SCENE } from '../../../config/map-scene';
import { DragCoordinationProvider, HORIZONTAL_ROTATION, PointInsertOverlay } from '../../../lib/drawing';
import { useRuler } from '../../../lib/hooks/useRuler';
import { useGroundPointerContext } from '../../GroundPointerProvider';
import { useMapCameraContext } from '../../MapCameraProvider';

import { RulerLines } from './RulerLines';
import { RulerPoints } from './RulerPoints';

/** Размер невидимой плоскости для обработки кликов по линейке. */
const PLANE_SIZE = 10_000;

/**
 * Слой линейки на карте.
 */
export function RulerLayer() {
  const { controlsRef } = useMapCameraContext();
  const { pointerRef } = useGroundPointerContext();

  const { points, segments, insertPoint, handleClick, handlePointerDown, movePoint, removePoint } = useRuler();

  const handleInsert = (segmentId: string, x: number, z: number) => insertPoint(Number(segmentId) + 1, x, z);

  return (
    <DragCoordinationProvider controlsRef={controlsRef}>
      <mesh
        position={[0, MAP_SCENE.RULER_Y - 0.1, 0]}
        rotation={HORIZONTAL_ROTATION}
        onPointerDown={handlePointerDown}
        onClick={handleClick}
      >
        <planeGeometry args={[PLANE_SIZE, PLANE_SIZE]} />
        <meshBasicMaterial
          transparent
          opacity={0}
          depthWrite={false}
        />
      </mesh>

      {points.length >= 2 && <RulerLines points={points} />}

      <PointInsertOverlay
        points={points}
        segments={segments}
        onInsert={handleInsert}
        onMove={movePoint}
        y={MAP_SCENE.RULER_Y}
        pointerRef={pointerRef}
        ghostColor="#FEFCF9"
        pointSize={6}
        hitRadius={6}
      />

      <RulerPoints
        points={points}
        movePoint={movePoint}
        removePoint={removePoint}
      />
    </DragCoordinationProvider>
  );
}
