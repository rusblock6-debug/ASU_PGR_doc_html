import type { ThreeEvent } from '@react-three/fiber';
import { skipToken } from '@reduxjs/toolkit/query';
import { useState } from 'react';

import { useGetHorizonGraphQuery } from '@/shared/api/endpoints/horizons';
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
import {
  graphEditActions,
  removeNode,
  selectDraftEdges,
  selectDraftNodes,
  selectDraftNodesMap,
  selectPreviewColor,
  splitEdge,
} from '../../../model/graph';
import { selectSelectedHorizonId } from '../../../model/selectors';
import { useGroundPointerContext } from '../../GroundPointerProvider';
import { useMapCameraContext } from '../../MapCameraProvider';

import { Edge } from './Edge';
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
  const { data: graphData } = useGetHorizonGraphQuery(horizonId ?? skipToken);
  const previewColor = useAppSelector(selectPreviewColor);
  const horizonColor = previewColor ?? graphData?.horizon.color;

  const nodes = useAppSelector(selectDraftNodes);
  const nodesMap = useAppSelector(selectDraftNodesMap);
  const edges = useAppSelector(selectDraftEdges);

  const edgeSegments = buildEdgeSegments(edges, nodesMap);

  const handleClick = (event: ThreeEvent<MouseEvent>) => {
    event.stopPropagation();
    if (!isClick(event)) return;

    const { x, z } = pointerRef.current;
    if (isNearAnyPoint(x, z, nodes, ROAD_GRAPH_POINT_HIT_RADIUS)) return;
    if (isNearAnySegment(x, z, edgeSegments, ROAD_GRAPH_SEGMENT_HIT_RADIUS)) return;

    if (!drawingFromNodeId && nodes.length > 0) return;

    const { payload } = dispatch(graphEditActions.addNode(x, z, drawingFromNodeId));
    setDrawingFromNodeId(payload.tempId);
  };

  const handleAddEdge = (fromId: string, toId: string) => {
    dispatch(graphEditActions.addEdge(fromId, toId));
  };

  const handleSplitEdge = (edgeId: string, x: number, z: number) => {
    return dispatch(splitEdge(edgeId, x, z));
  };

  const handleMoveNode = (tempId: string, x: number, z: number) => {
    dispatch(graphEditActions.moveNode({ tempId, x, z }));
  };

  const handleRemoveNode = (tempId: string) => {
    if (drawingFromNodeId === tempId) setDrawingFromNodeId(null);
    dispatch(removeNode(tempId));
  };

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
        nodes={nodes}
        addEdge={handleAddEdge}
        moveNode={handleMoveNode}
        removeNode={handleRemoveNode}
        drawingFromNodeId={drawingFromNodeId}
        startDrawingFrom={setDrawingFromNodeId}
        cancelDrawing={() => setDrawingFromNodeId(null)}
        color={horizonColor}
      />

      {edges.map((edge) => {
        const from = nodesMap.get(edge.fromId);
        const to = nodesMap.get(edge.toId);
        if (!from || !to) return null;

        return (
          <Edge
            key={edge.tempId}
            from={from}
            to={to}
            color={horizonColor}
          />
        );
      })}

      <PointInsertOverlay
        points={nodes}
        segments={edgeSegments}
        y={MAP_SCENE.ROAD_GRAPH_Y}
        pointerRef={pointerRef}
        onInsert={handleSplitEdge}
        onMove={handleMoveNode}
        ghostColor={horizonColor ?? MAP_SCENE.ROAD_GRAPH.GHOST_NODE_COLOR}
        ghostBorderWidth={MAP_SCENE.ROAD_GRAPH.GHOST_NODE_BORDER_WIDTH}
        ghostBorderColor={MAP_SCENE.ROAD_GRAPH.GHOST_NODE_BORDER_COLOR}
        pointSize={ROAD_GRAPH_POINT_HIT_RADIUS}
        hitRadius={ROAD_GRAPH_SEGMENT_HIT_RADIUS}
        deferMove
      />

      <PreviewEdge
        drawingFromNodeId={drawingFromNodeId}
        nodesMap={nodesMap}
        color={horizonColor}
      />
    </DragCoordinationProvider>
  );
}
