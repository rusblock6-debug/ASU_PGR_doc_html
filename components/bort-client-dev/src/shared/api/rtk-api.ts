import type { BaseQueryFn, FetchArgs, FetchBaseQueryError } from '@reduxjs/toolkit/query/react';
import { createApi, fetchBaseQuery } from '@reduxjs/toolkit/query/react';

const API_BASE_URLS = {
  default: (import.meta.env.VITE_API_URL || '') + '/api',
  tripRoot: import.meta.env.VITE_API_URL || '',
  graph: (import.meta.env.VITE_GRAPH_API_URL || '') + '/graph-api',
  enterprise: (import.meta.env.VITE_ENTERPRISE_API_URL || '') + '/enterprise-api',
} as const;

export type ApiBackend = keyof typeof API_BASE_URLS;

const baseQueries = Object.fromEntries(
  Object.entries(API_BASE_URLS).map(([key, baseUrl]) => [key, fetchBaseQuery({ baseUrl })]),
) as Record<ApiBackend, ReturnType<typeof fetchBaseQuery>>;

/** Роутит запрос на нужный baseQuery в зависимости от `extraOptions.backend`. */
const dynamicBaseQuery: BaseQueryFn<string | FetchArgs, unknown, FetchBaseQueryError, { backend?: ApiBackend }> = (
  args,
  api,
  extraOptions,
) => {
  const backend = extraOptions?.backend ?? 'default';
  return baseQueries[backend](args, api, extraOptions);
};

export const rtkApi = createApi({
  reducerPath: 'api',
  baseQuery: dynamicBaseQuery,
  tagTypes: ['ShiftTask', 'RouteTask', 'ActiveTask', 'VehicleState', 'Place', 'Tag', 'Route', 'LoadType', 'Vehicle'],
  endpoints: () => ({}),
});
