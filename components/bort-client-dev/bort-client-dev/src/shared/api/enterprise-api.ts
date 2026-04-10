import { createApi, fetchBaseQuery } from '@reduxjs/toolkit/query/react';

const BASE_URL = (import.meta.env.VITE_ENTERPRISE_API_URL || '') + '/enterprise-api';

export const enterpriseApi = createApi({
  reducerPath: 'enterpriseApi',
  baseQuery: fetchBaseQuery({ baseUrl: BASE_URL }),
  tagTypes: ['LoadType', 'Vehicle'],
  endpoints: () => ({}),
});
