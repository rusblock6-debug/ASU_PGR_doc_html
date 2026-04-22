/** Ответ GET /api/route/{start}/{target} — поля зависят от OpenAPI graph-service. */
export type RouteBetweenNodesResponse = Readonly<Record<string, unknown>>;

/** Ответ GET /api/route/progress/... — поля зависят от OpenAPI graph-service. */
export type RouteProgressResponse = Readonly<Record<string, unknown>>;

/** Аргументы запроса маршрута между двумя узлами графа. */
export interface GetRouteBetweenNodesArgs {
  readonly startNodeId: number;
  readonly targetNodeId: number;
}

/** Аргументы запроса прогресса по маршруту (узлы + текущие координаты). */
export interface GetRouteProgressArgs {
  readonly startNodeId: number;
  readonly targetNodeId: number;
  readonly lat: number;
  readonly lon: number;
}
