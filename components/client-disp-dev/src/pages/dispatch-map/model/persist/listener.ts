import type { TypedStartListening } from '@reduxjs/toolkit';

import type { PersistSyncConfig } from './types';

type AppStartListening = TypedStartListening<RootState, AppDispatch>;

/**
 * Регистрирует единый слушатель, который отслеживает изменения
 * всех персистентных полей слайса карты и сохраняет их в LocalStorage.
 *
 * Сравнивает ссылки до/после каждого экшна.
 */
export function setupMapPersistListeners(startListening: AppStartListening, configs: readonly PersistSyncConfig[]) {
  startListening({
    predicate: (_action, currentState, previousState) =>
      configs.some((c) => c.selector(currentState.map) !== c.selector(previousState.map)),
    effect: (_action, listenerApi) => {
      const current = listenerApi.getState().map;
      const prev = listenerApi.getOriginalState().map;
      for (const config of configs) {
        if (config.selector(current) !== config.selector(prev)) {
          localStorage.setItem(config.key, JSON.stringify(config.selector(current)));
        }
      }
    },
  });
}
