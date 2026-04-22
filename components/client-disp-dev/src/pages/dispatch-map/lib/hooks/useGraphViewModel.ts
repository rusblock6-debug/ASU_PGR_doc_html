import { skipToken } from '@reduxjs/toolkit/query';

import { useGetHorizonGraphQuery } from '@/shared/api/endpoints/horizons';
import { useAppSelector } from '@/shared/lib/hooks/useAppSelector';

import { MAP_SCENE } from '../../config/map-scene';
import { selectPreviewColor, serverToEditor } from '../../model/graph';
import { selectSelectedHorizonId } from '../../model/selectors';

/**
 * Хук для просмотра слоя дорожного графа.
 *
 * Трансформирует данные из RTK Query ({@link useGetHorizonGraphQuery})
 * через {@link serverToEditor} в клиентские типы (`GraphNode` / `GraphEdge`),
 * предоставляя единый формат данных, совместимый с режимом редактирования.
 */
export function useGraphViewModel() {
  const previewColor = useAppSelector(selectPreviewColor);
  const horizonId = useAppSelector(selectSelectedHorizonId);
  const { data } = useGetHorizonGraphQuery(horizonId ?? skipToken);
  if (!data) return null;

  const storedRoadColor = data.horizon.color;
  const roadColor = previewColor ?? storedRoadColor ?? MAP_SCENE.ROAD_GRAPH.EDGE_COLOR;

  const { nodes, edges } = serverToEditor(data);
  const nodesMap = new Map(nodes.map((node) => [node.tempId, node]));

  return { nodes, edges, nodesMap, roadColor };
}
