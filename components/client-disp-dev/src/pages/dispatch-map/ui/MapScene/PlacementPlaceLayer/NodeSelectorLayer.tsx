import { useThree } from '@react-three/fiber';
import { skipToken } from '@reduxjs/toolkit/query';
import { useEffect } from 'react';

import { useGetHorizonGraphQuery } from '@/shared/api/endpoints/horizons';
import { useAppDispatch } from '@/shared/lib/hooks/useAppDispatch';
import { useAppSelector } from '@/shared/lib/hooks/useAppSelector';

import { MAP_SCENE } from '../../../config/map-scene';
import { toScene } from '../../../lib/coordinates';
import { DragCoordinationProvider, CirclePoint } from '../../../lib/drawing';
import { selectSelectedHorizonId } from '../../../model/selectors';
import { mapActions } from '../../../model/slice';
import type { PlacementPlace } from '../../../model/types';
import { useMapCameraContext } from '../../MapCameraProvider';

/**
 * Представляет свойства компонента {@link NodeSelectorLayer}.
 */
interface NodeSelectorLayerProps {
  /** Возвращает место для размещения на карте. */
  readonly placementPlace: PlacementPlace;
}

/**
 * Слой выбора вершины дорожного графа при размещении места.
 * Отображает вершины как кликабельные круги.
 */
export function NodeSelectorLayer({ placementPlace }: NodeSelectorLayerProps) {
  const dispatch = useAppDispatch();
  const { gl } = useThree();
  const { controlsRef } = useMapCameraContext();
  const horizonId = useAppSelector(selectSelectedHorizonId);
  const { data: graphData } = useGetHorizonGraphQuery(horizonId ?? skipToken);
  const nodeColor = graphData?.horizon.color;

  useEffect(() => {
    return () => {
      gl.domElement.style.cursor = '';
    };
  }, [gl]);

  const handleHoverChange = (_id: string, isHovered: boolean) => {
    gl.domElement.style.cursor = isHovered ? 'pointer' : 'none';
  };

  const handleClick = (sceneX: number, sceneZ: number, nodeId: number) => {
    dispatch(
      mapActions.setPlacementPlaceToAdd({
        placeType: placementPlace.placeType,
        position: [sceneX, MAP_SCENE.ROAD_GRAPH_Y, sceneZ],
        isPlacementMode: false,
        nodeId,
      }),
    );
  };

  if (!graphData) return null;

  return (
    <DragCoordinationProvider controlsRef={controlsRef}>
      <group>
        {graphData.nodes.map((node) => {
          const [sceneX, , sceneZ] = toScene(node.x, node.y);

          return (
            <CirclePoint
              key={node.id}
              id={String(node.id)}
              x={sceneX}
              y={MAP_SCENE.ROAD_GRAPH_Y + MAP_SCENE.POINT_ABOVE_LAYER_Y}
              z={sceneZ}
              size={MAP_SCENE.ROAD_GRAPH.NODE_SIZE}
              color={nodeColor}
              hoverColor={MAP_SCENE.ROAD_GRAPH.GHOST_NODE_COLOR}
              borderColor={MAP_SCENE.ROAD_GRAPH.NODE_BORDER_COLOR}
              onClick={() => handleClick(sceneX, sceneZ, node.id)}
              onHoverChange={handleHoverChange}
            />
          );
        })}
      </group>
    </DragCoordinationProvider>
  );
}
