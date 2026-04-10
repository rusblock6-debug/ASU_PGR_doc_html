import { Line } from '@react-three/drei';
import { skipToken } from '@reduxjs/toolkit/query';

import { useGetHorizonGraphQuery } from '@/shared/api/endpoints/horizons';
import { useAppSelector } from '@/shared/lib/hooks/useAppSelector';

import { MAP_SCENE } from '../../../config/map-scene';
import { toScene } from '../../../lib/coordinates';
import { selectPreviewColor } from '../../../model/graph';
import { selectSelectedHorizonId } from '../../../model/selectors';

/**
 * Слой дорожного графа на карте.
 */
export function RoadGraphLayer() {
  const horizonId = useAppSelector(selectSelectedHorizonId);
  const { data } = useGetHorizonGraphQuery(horizonId ?? skipToken);
  const previewColor = useAppSelector(selectPreviewColor);

  if (!data) return null;

  const edgeColor = previewColor ?? data.horizon.color ?? MAP_SCENE.ROAD_GRAPH.EDGE_COLOR;

  const nodesMap = new Map(
    data.nodes.map((node) => {
      const [x, , z] = toScene(node.x, node.y);
      return [node.id, { x, z }];
    }),
  );

  return (
    <group>
      {data.edges.map((edge) => {
        const from = nodesMap.get(edge.from_node_id);
        const to = nodesMap.get(edge.to_node_id);
        if (!from || !to) return null;

        return (
          <Line
            key={edge.id}
            points={[
              [from.x, MAP_SCENE.ROAD_GRAPH_Y, from.z],
              [to.x, MAP_SCENE.ROAD_GRAPH_Y, to.z],
            ]}
            color={edgeColor}
            lineWidth={MAP_SCENE.ROAD_GRAPH.EDGE_WIDTH}
          />
        );
      })}
    </group>
  );
}
