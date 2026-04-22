import { configureStore } from '@reduxjs/toolkit';
import { setupListeners } from '@reduxjs/toolkit/query';

import { graphEditReducer, mapReducer } from '@/pages/dispatch-map';
import { workOrderReducer } from '@/pages/work-order';

import { authReducer } from '@/entities/user';

import { rtkApi } from '@/shared/api';

import { listenerMiddleware, setupAuthStorageSync } from './listener-middleware';

export const store = configureStore({
  reducer: {
    [rtkApi.reducerPath]: rtkApi.reducer,
    auth: authReducer,
    map: mapReducer,
    graphEdit: graphEditReducer,
    workOrder: workOrderReducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware().prepend(listenerMiddleware.middleware).concat(rtkApi.middleware),
  devTools:
    import.meta.env.MODE !== 'production'
      ? {
          actionsDenylist: [
            'api/queries/queryResultPatched',
            'api/invalidation/updateProvidedBy',
            'api/internalSubscriptions/subscriptionsUpdated',
          ],
        }
      : false,
});

setupListeners(store.dispatch);
setupAuthStorageSync(store.dispatch);
