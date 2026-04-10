/** Имя из graph-api или подпись по id места. */
const graphNameOrFallback = (placeId: number, graphName?: string | null) => {
  if (typeof graphName === 'string' && graphName.trim()) {
    return graphName.trim();
  }
  return `Место ${placeId}`;
};

/**
 * Подпись места из route_data, затем name из graph-api, иначе fallback по id.
 */
export const getPlaceLabelFromRouteData = (
  placeId: number,
  routeData: Record<string, unknown> | null,
  key: 'place_a_name' | 'place_b_name',
  graphName?: string | null,
) => {
  if (!routeData) {
    return graphNameOrFallback(placeId, graphName);
  }

  const fallbackKeys =
    key === 'place_a_name'
      ? ['place_a_name', 'place_a', 'from', 'from_name', 'start_place_name', 'start_point_name']
      : ['place_b_name', 'place_b', 'to', 'to_name', 'end_place_name', 'end_point_name'];

  for (const candidateKey of fallbackKeys) {
    const value = routeData[candidateKey];
    if (typeof value === 'string' && value.trim()) {
      return value;
    }
  }

  return graphNameOrFallback(placeId, graphName);
};

/**
 * Тип груза: приоритет полей route_data, затем name из enterprise (по graph place.cargo_type), иначе type_task.
 */
export const getCargoLabel = (
  typeTask: string,
  routeData: Record<string, unknown> | null,
  enterpriseLoadTypeName?: string | null,
) => {
  const cargo = routeData?.cargo_name ?? routeData?.load_type_name;
  if (typeof cargo === 'string' && cargo.trim()) {
    return cargo;
  }
  if (typeof enterpriseLoadTypeName === 'string' && enterpriseLoadTypeName.trim()) {
    return enterpriseLoadTypeName.trim();
  }
  return typeTask.replaceAll('_', ' ');
};
