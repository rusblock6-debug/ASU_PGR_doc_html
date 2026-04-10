import { createApi, fetchBaseQuery } from '@reduxjs/toolkit/query/react';

const BASE_URL = (import.meta.env.VITE_API_URL || '') + '/api';

export const rtkApi = createApi({
  reducerPath: 'api',
  baseQuery: fetchBaseQuery({
    baseUrl: BASE_URL,
  }),
  tagTypes: ['ShiftTask', 'RouteTask', 'ActiveTask', 'VehicleState'],
  endpoints: () => ({}),
});
