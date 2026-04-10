import { createListenerMiddleware } from '@reduxjs/toolkit';

import { MAP_PERSIST_CONFIGS, setupMapPersistListeners } from '@/pages/dispatch-map';

export const listenerMiddleware = createListenerMiddleware();

const startAppListening = listenerMiddleware.startListening.withTypes<RootState, AppDispatch>();

setupMapPersistListeners(startAppListening, MAP_PERSIST_CONFIGS);
