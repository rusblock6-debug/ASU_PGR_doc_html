import type { ThreeEvent } from '@react-three/fiber';
import { useState } from 'react';

import { useGetAllHorizonsQuery } from '@/shared/api/endpoints/horizons';
import { hasValue } from '@/shared/lib/has-value';
import { useAppDispatch } from '@/shared/lib/hooks/useAppDispatch';
import { useAppSelector } from '@/shared/lib/hooks/useAppSelector';

import { MAP_SCENE } from '../../../config/map-scene';
import {
  buildEdgeSegments,
  DragCoordinationProvider,
  HORIZONTAL_ROTATION,
  isNearAnyPoint,
  isNearAnySegment,
  PointInsertOverlay,
  useClickGuard,
} from '../../../lib/drawing';
import { getLadderEdgeColor } from '../../../lib/horizon-colors';
import {
  GraphElementType,
  graphEditActions,
  removeNode,
  selectDraftEdges,
  selectDraftNodes,
  selectDraftNodesMap,
  selectPreviewColor,
  selectRoadColor,
  splitEdge,
} from '../../../model/graph';
import { selectSelectedHorizonId } from '../../../model/selectors';
import { useGroundPointerContext } from '../../GroundPointerProvider';
import { useMapCameraContext } from '../../MapCameraProvider';

import { DraggableEdge } from './DraggableEdge';
import { PreviewEdge } from './PreviewEdge';
import { RoadGraphNodes } from './RoadGraphNodes';

/** Размер невидимой плоскости для обработки кликов. */
const PLANE_SIZE = 10_000;

/** Радиус зоны вокруг узла графа, в которой клик по плоскости игнорируется. */
const ROAD_GRAPH_POINT_HIT_RADIUS = 5;

/** Максимальное расстояние до сегмента графа, при котором клик считается попаданием в него. */
const ROAD_GRAPH_SEGMENT_HIT_RADIUS = 8;

/**
 * Слой редактирования дорожного графа на карте.
 */
export function RoadGraphEditLayer() {
  const dispatch = useAppDispatch();
  const { controlsRef } = useMapCameraContext();
  const { pointerRef } = useGroundPointerContext();
  const { handlePointerDown, isClick } = useClickGuard();

  const [drawingFromNodeId, setDrawingFromNodeId] = useState<string | null>(null);

  const horizonId = useAppSelector(selectSelectedHorizonId);
  const previewColor = useAppSelector(selectPreviewColor);
  const storedRoadColor = useAppSelector(selectRoadColor);
  const { data: horizonsData } = useGetAllHorizonsQuery();

  const nodes = useAppSelector(selectDraftNodes);
  const edges = useAppSelector(selectDraftEdges);

  const roadNodes = nodes.filter((node) => node.horizonId === horizonId);
  const roadEdges = edges.filter((edge) => edge.edgeType !== GraphElementType.LADDER);
  const ladderEdges = edges.filter((edge) => edge.edgeType === GraphElementType.LADDER);

  const roadColor = previewColor ?? storedRoadColor ?? MAP_SCENE.ROAD_GRAPH.EDGE_COLOR;

  const nodesMap = useAppSelector(selectDraftNodesMap);
  const roadEdgeSegments = buildEdgeSegments(roadEdges, nodesMap);

  const handleClick = (event: ThreeEvent<MouseEvent>) => {
    event.stopPropagation();
    if (!isClick(event)) return;

    const { x, z } = pointerRef.current;
    if (isNearAnyPoint(x, z, nodes, ROAD_GRAPH_POINT_HIT_RADIUS)) return;
    if (isNearAnySegment(x, z, roadEdgeSegments, ROAD_GRAPH_SEGMENT_HIT_RADIUS)) return;

    if (!drawingFromNodeId && roadNodes.length > 0) return;

    const { payload } = dispatch(graphEditActions.addNode(x, z, drawingFromNodeId, horizonId));
    setDrawingFromNodeId(payload.tempId);
  };

  const handleAddEdge = (fromId: string, toId: string) => {
    dispatch(graphEditActions.addEdge(fromId, toId));
  };

  const handleSplitEdge = (edgeId: string, x: number, z: number) => {
    return dispatch(splitEdge(edgeId, x, z, horizonId));
  };

  const handleMoveNode = (tempId: string, x: number, z: number) => {
    dispatch(graphEditActions.moveNode({ tempId, x, z }));
  };

  const handleRemoveNode = (tempId: string) => {
    if (drawingFromNodeId === tempId) setDrawingFromNodeId(null);
    dispatch(removeNode(tempId));
  };

  if (!hasValue(horizonId)) {
    return null;
  }

  return (
    <DragCoordinationProvider controlsRef={controlsRef}>
      <mesh
        position={[0, MAP_SCENE.ROAD_GRAPH_Y - 0.1, 0]}
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

      <RoadGraphNodes
        nodes={roadNodes}
        addEdge={handleAddEdge}
        moveNode={handleMoveNode}
        removeNode={handleRemoveNode}
        drawingFromNodeId={drawingFromNodeId}
        startDrawingFrom={setDrawingFromNodeId}
        cancelDrawing={() => setDrawingFromNodeId(null)}
        color={roadColor}
      />

      {roadEdges.map((edge) => {
        const from = nodesMap.get(edge.fromId);
        const to = nodesMap.get(edge.toId);
        if (!from || !to) return null;

        return (
          <DraggableEdge
            key={edge.tempId}
            from={from}
            to={to}
            color={roadColor}
          />
        );
      })}

      {ladderEdges.map((edge) => {
        const from = nodesMap.get(edge.fromId);
        const to = nodesMap.get(edge.toId);
        if (!from || !to) return null;

        const color = getLadderEdgeColor({
          edge,
          nodesMap,
          currentHorizonId: horizonId,
          horizons: horizonsData?.items,
          fallbackColor: roadColor,
        });

        return (
          <DraggableEdge
            key={edge.tempId}
            from={from}
            to={to}
            color={color}
          />
        );
      })}

      <PointInsertOverlay
        points={roadNodes}
        segments={roadEdgeSegments}
        y={MAP_SCENE.ROAD_GRAPH_Y}
        pointerRef={pointerRef}
        onInsert={handleSplitEdge}
        onMove={handleMoveNode}
        ghostColor={roadColor}
        ghostBorderWidth={MAP_SCENE.ROAD_GRAPH.GHOST_NODE_BORDER_WIDTH}
        ghostBorderColor={MAP_SCENE.ROAD_GRAPH.GHOST_NODE_BORDER_COLOR}
        pointSize={ROAD_GRAPH_POINT_HIT_RADIUS}
        hitRadius={ROAD_GRAPH_SEGMENT_HIT_RADIUS}
        deferMove
      />

      <PreviewEdge
        drawingFromNodeId={drawingFromNodeId}
        nodesMap={nodesMap}
        color={roadColor}
      />
    </DragCoordinationProvider>
  );
}
