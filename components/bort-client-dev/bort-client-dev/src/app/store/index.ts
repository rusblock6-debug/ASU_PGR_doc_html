import { configureStore } from '@reduxjs/toolkit';
import { setupListeners } from '@reduxjs/toolkit/query';

import { rtkApi } from '@/shared/api';
import { enterpriseApi } from '@/shared/api/enterprise-api';
import { graphApi } from '@/shared/api/graph-api';
import { routeStreamSlice } from '@/shared/lib/route-stream';
import { vehicleEventsSlice } from '@/shared/lib/vehicle-events';

import { listenerMiddleware } from './listener-middleware';

export const store = configureStore({
  reducer: {
    [rtkApi.reducerPath]: rtkApi.reducer,
    [graphApi.reducerPath]: graphApi.reducer,
    [enterpriseApi.reducerPath]: enterpriseApi.reducer,
    [vehicleEventsSlice.name]: vehicleEventsSlice.reducer,
    [routeStreamSlice.name]: routeStreamSlice.reducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware()
      .prepend(listenerMiddleware.middleware)
      .concat(rtkApi.middleware, graphApi.middleware, enterpriseApi.middleware),
  devTools: import.meta.env.MODE !== 'production',
});

setupListeners(store.dispatch);
