import { configureStore } from '@reduxjs/toolkit';
import { setupListeners } from '@reduxjs/toolkit/query';

import { graphEditReducer, mapReducer } from '@/pages/dispatch-map';
import { workOrderReducer } from '@/pages/work-order';

import { rtkApi } from '@/shared/api';

import { listenerMiddleware } from './listener-middleware';

export const store = configureStore({
  reducer: {
    [rtkApi.reducerPath]: rtkApi.reducer,
    map: mapReducer,
    graphEdit: graphEditReducer,
    workOrder: workOrderReducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware().prepend(listenerMiddleware.middleware).concat(rtkApi.middleware),
  devTools: import.meta.env.MODE !== 'production',
});

setupListeners(store.dispatch);
