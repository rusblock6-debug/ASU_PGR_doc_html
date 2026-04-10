import { graphApi } from '@/shared/api/graph-api';

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

const routesApi = graphApi.injectEndpoints({
  endpoints: (builder) => ({
    getRouteBetweenNodes: builder.query<RouteBetweenNodesResponse, GetRouteBetweenNodesArgs>({
      query: ({ startNodeId, targetNodeId }) =>
        `/api/route/${encodeURIComponent(String(startNodeId))}/${encodeURIComponent(String(targetNodeId))}`,
      providesTags: (_result, _error, { startNodeId, targetNodeId }) => [
        { type: 'Route' as const, id: `between:${startNodeId}:${targetNodeId}` },
      ],
    }),
    getRouteProgress: builder.query<RouteProgressResponse, GetRouteProgressArgs>({
      query: ({ startNodeId, targetNodeId, lat, lon }) => {
        const params = new URLSearchParams();
        params.set('lat', String(lat));
        params.set('lon', String(lon));
        return `/api/route/progress/${encodeURIComponent(String(startNodeId))}/${encodeURIComponent(String(targetNodeId))}?${params.toString()}`;
      },
      providesTags: (_result, _error, { startNodeId, targetNodeId }) => [
        { type: 'Route' as const, id: `progress:${startNodeId}:${targetNodeId}` },
      ],
    }),
  }),
});

export const { useGetRouteBetweenNodesQuery, useGetRouteProgressQuery } = routesApi;
