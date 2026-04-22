import type { BaseQueryFn, FetchArgs, FetchBaseQueryError } from '@reduxjs/toolkit/query';
import { fetchBaseQuery } from '@reduxjs/toolkit/query';

import { BASE_URL } from '@/shared/api/api-constants';
import { ensureRefresh } from '@/shared/api/utils/ensure-refresh';
import { authLogout } from '@/shared/lib/auth-actions';
import { tokenStorage } from '@/shared/lib/token-storage';
import { getRouteForbidden } from '@/shared/routes/router';

export { BASE_URL };

/**
 * Доп. опции для baseQuery (настраиваются на уровне endpoint).
 */
interface ExtraOptions {
  /** Флаг пропуска повторной авторизации. */
  readonly skipReauth?: boolean;
}

/**
 * Сигнатура {@link BaseQueryFn} для HTTP-запросов с поддержкой:
 * - подстановки `Authorization` из хранилища;
 * - при `401` — refresh и один повтор запроса, при неуспехе — `authLogout`;
 * - при `403` с валидным access — редирект на Forbidden (если не на ней уже);
 * - опции {@link ExtraOptions.skipReauth} отключает эту логику для конкретного endpoint.
 */
type BaseQueryWithReauth = BaseQueryFn<string | FetchArgs, unknown, FetchBaseQueryError, ExtraOptions>;

/**
 * BaseQuery без reauth — подставляет `Authorization`, если access token существует.
 */
const rawBaseQuery = fetchBaseQuery({
  baseUrl: BASE_URL,
  prepareHeaders: (headers) => {
    const token = tokenStorage.getAccessToken();

    if (token) {
      headers.set('Authorization', `Bearer ${token}`);
    }

    return headers;
  },
});

/**
 * Проставляет заголовок Authorization для повторного запроса.
 */
const withAccessToken = (args: string | FetchArgs, accessToken: string | null): FetchArgs => {
  const normalized: FetchArgs = typeof args === 'string' ? { url: args } : args;

  if (!accessToken) {
    return normalized;
  }

  return {
    ...normalized,
    headers: {
      ...(normalized.headers as Record<string, string> | undefined),
      Authorization: `Bearer ${accessToken}`,
    },
  };
};

/**
 * Перенаправляет на Forbidden (если это не текущая страница).
 */
const redirectToForbidden = () => {
  const forbiddenPath = getRouteForbidden();

  if (typeof window === 'undefined') {
    return;
  }

  if (window.location.pathname === forbiddenPath) {
    return;
  }

  window.location.assign(forbiddenPath);
};

/**
 * BaseQuery для RTK Query с автоматическим refresh токена при 401.
 */
export const baseQueryWithReauth: BaseQueryWithReauth = async (args, api, extraOptions) => {
  const result = await rawBaseQuery(args, api, extraOptions);

  if (extraOptions?.skipReauth) {
    return result;
  }

  if (result.error?.status === 403) {
    if (tokenStorage.getAccessToken()) {
      redirectToForbidden();
    }
    return result;
  }

  if (result.error?.status !== 401) {
    return result;
  }

  const refreshToken = tokenStorage.getRefreshToken();
  const outcome = await ensureRefresh(refreshToken, api.dispatch);

  if (outcome === 'failed') {
    return result;
  }

  if (outcome === 'invalid') {
    api.dispatch(authLogout());
    return result;
  }

  const accessToken = tokenStorage.getAccessToken();
  const retryResult = await rawBaseQuery(withAccessToken(args, accessToken), api, extraOptions);

  if (retryResult.error?.status === 401) {
    api.dispatch(authLogout());
    return retryResult;
  }

  if (retryResult.error?.status === 403) {
    if (tokenStorage.getAccessToken()) {
      redirectToForbidden();
    }
    return retryResult;
  }

  return retryResult;
};
