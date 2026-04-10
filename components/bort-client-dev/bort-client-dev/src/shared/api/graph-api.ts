import { createApi, fetchBaseQuery } from '@reduxjs/toolkit/query/react';

const BASE_URL = (import.meta.env.VITE_GRAPH_API_URL || '') + '/graph-api';

export const graphApi = createApi({
  reducerPath: 'graphApi',
  baseQuery: fetchBaseQuery({ baseUrl: BASE_URL }),
  tagTypes: ['Place', 'Tag', 'Route'],
  endpoints: () => ({}),
});
