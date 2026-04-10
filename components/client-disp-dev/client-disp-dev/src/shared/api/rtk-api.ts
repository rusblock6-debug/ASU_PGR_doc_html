import { createApi, fetchBaseQuery } from '@reduxjs/toolkit/query/react';

const BASE_URL = (import.meta.env.VITE_API_URL || '') + '/api';

export const rtkApi = createApi({
  reducerPath: 'api',
  baseQuery: fetchBaseQuery({
    baseUrl: BASE_URL,
  }),
  tagTypes: [
    'Trips',
    'Places',
    'Vehicle',
    'Equipment',
    'Horizons',
    'Statuses',
    'Organization-categories',
    'Analytic-categories',
    'Shafts',
    'Sections',
    'Tag',
    'Load-types',
    'Load-type-categories',
    'Shift-tasks',
    'Roles',
    'Staff',
    'Staff-position',
    'Staff-department',
    'Substrates',
    'Fleet-control',
    'Fleet-control-vehicle-tooltip',
    'Fleet-control-shift-load-type-volumes',
  ],
  endpoints: () => ({}),
});
