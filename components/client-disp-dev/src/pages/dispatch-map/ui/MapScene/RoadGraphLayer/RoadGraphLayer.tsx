import { useGetAllHorizonsQuery } from '@/shared/api/endpoints/horizons';
import { hasValue } from '@/shared/lib/has-value';
import { useAppSelector } from '@/shared/lib/hooks/useAppSelector';

import { useGraphViewModel } from '../../../lib/hooks/useGraphViewModel';
import { getLadderEdgeColor } from '../../../lib/horizon-colors';
import { GraphElementType } from '../../../model/graph';
import { selectSelectedHorizonId } from '../../../model/selectors';

import { Edge } from './Edge';

/**
 * Слой дорожного графа на карте.
 */
export function RoadGraphLayer() {
  const horizonId = useAppSelector(selectSelectedHorizonId);
  const { data: horizonsData } = useGetAllHorizonsQuery();
  const data = useGraphViewModel();

  if (!data || !hasValue(horizonId)) return null;

  const { edges, nodesMap, roadColor } = data;
  const roadEdges = edges.filter((edge) => edge.edgeType === GraphElementType.ROAD);
  const ladderEdges = edges.filter((edge) => edge.edgeType === GraphElementType.LADDER);

  return (
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
          horizons: horizonsData?.items,
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
    </group>
  );
}
