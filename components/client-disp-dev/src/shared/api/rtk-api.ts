import { createApi } from '@reduxjs/toolkit/query/react';

import { baseQueryWithReauth } from './base-query';

export const rtkApi = createApi({
  reducerPath: 'api',
  baseQuery: baseQueryWithReauth,
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
    'Ladders',
    'Fleet-control',
    'Fleet-control-vehicle-tooltip',
    'Fleet-control-shift-load-type-volumes',
  ],
  endpoints: () => ({}),
});
