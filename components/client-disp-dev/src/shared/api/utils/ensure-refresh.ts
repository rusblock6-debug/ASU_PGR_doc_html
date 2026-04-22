import { BASE_URL } from '@/shared/api/api-constants';
import type { TokenResponse } from '@/shared/api/endpoints/auth';
import { authTokensReceived } from '@/shared/lib/auth-actions';

const REFRESH_TIMEOUT_MS = 10_000;

/**
 * Результат попытки обновить access token по refresh token.
 *
 * - `refreshed` — новые токены получены и записаны в хранилище; запрос можно повторить.
 * - `invalid` — сессия недействительна (нет refresh, ответ 401/403 или неверное тело); вызывающий код обычно делает logout.
 * - `failed` — сетевая/серверная ошибка без явной инвалидации сессии; повтор запроса не выполняется, исходный ответ (например 401) сохраняется.
 */
export type RefreshOutcome = 'refreshed' | 'invalid' | 'failed';

let refreshPromise: Promise<RefreshOutcome> | null = null;

/**
 * Один refresh на все параллельные 401 (RTK Query, SSE и т.д.).
 */
export const ensureRefresh = (refreshToken: string | null, dispatch: AppDispatch): Promise<RefreshOutcome> => {
  if (!refreshToken) {
    return Promise.resolve<RefreshOutcome>('invalid');
  }

  if (!refreshPromise) {
    refreshPromise = (async () => {
      try {
        const res = await fetch(`${BASE_URL}/v1/auth/refresh?refresh_token=${encodeURIComponent(refreshToken)}`, {
          method: 'POST',
          signal: AbortSignal.timeout(REFRESH_TIMEOUT_MS),
        });

        if (!res.ok) {
          if (res.status === 401 || res.status === 403) {
            return 'invalid';
          }
          if (res.status >= 500) {
            return 'failed';
          }
          return 'invalid';
        }

        const data = (await res.json()) as TokenResponse;

        dispatch(authTokensReceived({ accessToken: data.access_token, refreshToken: data.refresh_token }));

        return 'refreshed';
      } catch {
        return 'failed';
      } finally {
        refreshPromise = null;
      }
    })();
  }

  return refreshPromise;
};
