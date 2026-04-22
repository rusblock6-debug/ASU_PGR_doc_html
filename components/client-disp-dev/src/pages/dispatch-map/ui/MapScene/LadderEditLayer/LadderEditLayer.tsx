import { useState } from 'react';

import { useDeleteLadderNodeMutation } from '@/shared/api/endpoints/ladder-nodes';
import { isHTTPError } from '@/shared/api/types';
import { hasValue } from '@/shared/lib/has-value';
import { useAppDispatch } from '@/shared/lib/hooks/useAppDispatch';
import { useAppSelector } from '@/shared/lib/hooks/useAppSelector';
import { toast } from '@/shared/ui/Toast';

import { MAP_SCENE } from '../../../config/map-scene';
import { CirclePoint, DragCoordinationProvider } from '../../../lib/drawing';
import { useGraphViewModel } from '../../../lib/hooks/useGraphViewModel';
import { useMapPlaces } from '../../../lib/hooks/useMapPlaces';
import { getLadderEdgeColor, getLadderNodeColor } from '../../../lib/horizon-colors';
import { GraphElementType, graphEditActions } from '../../../model/graph';
import { selectSelectedHorizonId } from '../../../model/selectors';
import { mapActions } from '../../../model/slice';
import { useMapCameraContext } from '../../MapCameraProvider';
import { Edge } from '../RoadGraphLayer/Edge';

import { LadderNodeTooltip } from './LadderNodeTooltip';

/**
 * Слой редактирования переездов (лестниц) между горизонтами.
 *
 * Показывает все вершины графа текущего горизонта.
 * Вершины с существующими переездами окрашиваются в цвет связанного горизонта.
 */
export function LadderEditLayer() {
  const dispatch = useAppDispatch();
  const { controlsRef } = useMapCameraContext();

  const horizonId = useAppSelector(selectSelectedHorizonId);
  const data = useGraphViewModel();
  const { horizons } = useMapPlaces();

  const [deleteLadder] = useDeleteLadderNodeMutation();
  const [activeTooltipNodeId, setActiveTooltipNodeId] = useState<number | null>(null);

  const handleNodeHover = (nodeId: string, isHovered: boolean) => {
    if (!isHovered) return;
    setActiveTooltipNodeId(Number(nodeId));
  };

  const handleSelectHorizon = (targetHorizonId: number, nodeId: number) => {
    if (!hasValue(horizonId)) return;

    dispatch(graphEditActions.setLadderSource({ nodeId, horizonId }));
    dispatch(mapActions.setSelectedHorizonId(targetHorizonId));
    setActiveTooltipNodeId(null);
  };

  const handleDeleteLadder = async (nodeId: number) => {
    try {
      await deleteLadder(nodeId);
      setActiveTooltipNodeId(null);
    } catch (error) {
      const detail = isHTTPError(error) ? error.detail : undefined;
      const errorDetails = typeof detail === 'string' ? `Ошибка: ${detail}` : '';
      toast.error({ message: `Не удалось удалить, попробуйте еще раз. ${errorDetails}` });
    }
  };

  if (!data || !hasValue(horizonId)) return null;

  const { nodes, edges, nodesMap, roadColor } = data;
  const roadEdges = edges.filter((edge) => edge.edgeType === GraphElementType.ROAD);
  const ladderEdges = edges.filter((edge) => edge.edgeType === GraphElementType.LADDER);
  const activeNode = nodes.find((node) => node.id === activeTooltipNodeId);

  return (
    <DragCoordinationProvider controlsRef={controlsRef}>
      <group>
        {roadEdges.map((edge) => {
          const from = nodesMap.get(edge.fromId);
          const to = nodesMap.get(edge.toId);
          if (!from || !to) return null;

          return (
            <Edge
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
            horizons,
            fallbackColor: roadColor,
          });

          return (
            <Edge
              key={edge.tempId}
              from={from}
              to={to}
              color={color}
            />
          );
        })}

        {nodes.map((node) => {
          if (!hasValue(node.id)) return null;

          const color = getLadderNodeColor({
            node,
            currentHorizonId: horizonId,
            horizons,
            fallbackColor: roadColor,
          });

          return (
            <CirclePoint
              key={node.tempId}
              id={String(node.id)}
              x={node.x}
              y={MAP_SCENE.ROAD_GRAPH_Y + MAP_SCENE.POINT_ABOVE_LAYER_Y}
              z={node.z}
              size={MAP_SCENE.ROAD_GRAPH.NODE_SIZE}
              color={color}
              borderColor={MAP_SCENE.ROAD_GRAPH.NODE_BORDER_COLOR}
              hoverColor={MAP_SCENE.ROAD_GRAPH.NODE_HOVER_BORDER_COLOR}
              onHoverChange={handleNodeHover}
            />
          );
        })}

        {activeNode && hasValue(activeNode.id) && (
          <LadderNodeTooltip
            nodeId={activeNode.id}
            position={[activeNode.x, MAP_SCENE.ROAD_GRAPH_Y, activeNode.z]}
            nodeType={activeNode.nodeType}
            nodeHorizonId={activeNode.horizonId}
            onDeleteLadder={() => handleDeleteLadder(activeNode.id)}
            onSelectHorizon={(targetId) => handleSelectHorizon(targetId, activeNode.id)}
            onClose={() => setActiveTooltipNodeId(null)}
          />
        )}
      </group>
    </DragCoordinationProvider>
  );
}
