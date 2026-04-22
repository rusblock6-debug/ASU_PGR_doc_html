import { type Dispatch, createListenerMiddleware } from '@reduxjs/toolkit';

import { MAP_PERSIST_CONFIGS, setupMapPersistListeners } from '@/pages/dispatch-map';

import { rtkApi } from '@/shared/api';
import { authLogout, authSyncFromStorage, authTokensReceived } from '@/shared/lib/auth-actions';
import { hasValue } from '@/shared/lib/has-value';
import { tokenStorage } from '@/shared/lib/token-storage';

export const listenerMiddleware = createListenerMiddleware();

const startAppListening = listenerMiddleware.startListening.withTypes<RootState, AppDispatch>();

setupMapPersistListeners(startAppListening, MAP_PERSIST_CONFIGS);

/**
 * Синхронизирует токены авторизации с `tokenStorage` при успешном логине или рефреше.
 * Нужно, чтобы `base-query` мог подставлять актуальный access-токен в заголовки запросов.
 */
startAppListening({
  actionCreator: authTokensReceived,
  effect: ({ payload }) => {
    tokenStorage.setTokens(payload.accessToken, payload.refreshToken);
  },
});

/**
 * Очищает токены и сбрасывает кеш RTK Query при логауте.
 * Сброс кеша гарантирует, что данные предыдущего пользователя не утекут в следующую сессию.
 */
startAppListening({
  actionCreator: authLogout,
  effect: (_, { dispatch }) => {
    tokenStorage.clear();
    dispatch(rtkApi.util.resetApiState());
  },
});

/**
 * Начальная синхронизация auth-состояния из storage + подписка на `storage`-события
 * для кросс-табовой синхронизации. Вызывать после создания стора.
 */
const getTokensPayload = () => ({
  accessToken: tokenStorage.getAccessToken(),
  refreshToken: tokenStorage.getRefreshToken(),
});

/**
 * Синхронизирует auth-состояние из tokenStorage и подписывается на `storage`-события
 * для кросс-табовой синхронизации. Вызывать после создания стора.
 *
 * @param dispatch - Redux dispatch для отправки `authSyncFromStorage`
 */
export function setupAuthStorageSync(dispatch: Dispatch) {
  dispatch(authSyncFromStorage(getTokensPayload()));

  window.addEventListener('storage', (event: StorageEvent) => {
    if (event.storageArea !== localStorage) {
      return;
    }

    if (!hasValue(event.key)) {
      dispatch(authSyncFromStorage(getTokensPayload()));
      return;
    }

    if (event.key === tokenStorage.ACCESS_TOKEN_KEY || event.key === tokenStorage.REFRESH_TOKEN_KEY) {
      dispatch(authSyncFromStorage(getTokensPayload()));
    }
  });
}
