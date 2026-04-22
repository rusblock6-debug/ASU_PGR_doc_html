import { fetchEventSource } from '@microsoft/fetch-event-source';

import { BASE_URL } from '@/shared/api/api-constants';
import { ensureRefresh, type RefreshOutcome } from '@/shared/api/utils/ensure-refresh';
import { authLogout } from '@/shared/lib/auth-actions';
import { hasValueNotEmpty } from '@/shared/lib/has-value';
import { tokenStorage } from '@/shared/lib/token-storage';
const SSE_RECONNECT_DELAY_MS = 3_000;

/** Путь относительно `/api`, как в RTK Query (`/trip/...`). Допустим legacy-вариант с префиксом `/api`. */
const resolveAuthenticatedSseUrl = (pathOrUrl: string) => {
  if (pathOrUrl.startsWith('http://') || pathOrUrl.startsWith('https://')) {
    return pathOrUrl;
  }
  let path = pathOrUrl.startsWith('/') ? pathOrUrl : `/${pathOrUrl}`;
  if (path === '/api' || path.startsWith('/api/')) {
    path = path === '/api' ? '/' : path.slice('/api'.length);
  }
  return `${BASE_URL}${path}`;
};

/**
 * Параметры для {@link createAuthenticatedSSE}: URL потока, Redux-dispatch,
 * жизненный цикл подписки RTK Query и обработчик событий.
 *
 */
interface CreateAuthenticatedSSEOptions {
  /**
   * Путь API без host, в том же виде, что и `query` в RTK
   * (например `/trip/events/stream/shift-tasks`). Абсолютный URL тоже допустим.
   */
  readonly url: string;
  /**
   * Redux `dispatch`: refresh access token при 401 и `authLogout` при неуспешном refresh.
   */
  readonly dispatch: AppDispatch;
  /**
   * Промис из streaming-эндпоинта RTK Query (`cacheDataLoaded`): ждём, пока подписка
   * реально поднимется, прежде чем открывать SSE.
   */
  readonly cacheDataLoaded: Promise<unknown>;
  /**
   * Промис из того же streaming-эндпоинта (`cacheEntryRemoved`): при resolve —
   * подписка снята, SSE нужно закрыть (`AbortController.abort`).
   */
  readonly cacheEntryRemoved: Promise<unknown>;
  /**
   * Вызывается для каждого успешно распарсенного JSON-сообщения из SSE (`event.data`).
   */
  readonly onMessage: (data: unknown) => void;
}

class FatalSSEError extends Error {}

/**
 * Подключает SSE-поток с авторизацией, refresh при 401 и фиксированным реконнектом каждые 3 секунды.
 * Завершает соединение при удалении cache entry.
 */
export const createAuthenticatedSSE = async ({
  url,
  dispatch,
  cacheDataLoaded,
  cacheEntryRemoved,
  onMessage,
}: CreateAuthenticatedSSEOptions) => {
  await cacheDataLoaded;

  const controller = new AbortController();
  const resolvedUrl = resolveAuthenticatedSseUrl(url);

  void fetchEventSource(resolvedUrl, {
    fetch(input, init) {
      return globalThis.fetch(input, {
        ...init,
        headers: {
          ...init?.headers,
          Authorization: `Bearer ${tokenStorage.getAccessToken() ?? ''}`,
        },
      });
    },
    signal: controller.signal,
    // Иначе браузер не держит соединение в фоне у скрытой вкладки
    openWhenHidden: true,
    async onopen(response) {
      if (response.ok) return;

      if (response.status === 401) {
        const outcome: RefreshOutcome = await ensureRefresh(tokenStorage.getRefreshToken(), dispatch);
        if (outcome === 'refreshed') {
          // onerror вернёт задержку и fetchEventSource переподключится со свежим токеном
          throw new Error('401 refreshed, reconnecting');
        }
        if (outcome === 'invalid') {
          dispatch(authLogout());
          throw new FatalSSEError('401 and refresh failed');
        }
        // transient (сеть / 5xx) — без logout, как в base-query
        throw new Error('401 refresh transient');
      }

      throw new Error(`SSE open failed: ${response.status}`);
    },
    onmessage(event) {
      try {
        if (hasValueNotEmpty(event.data)) {
          const data = JSON.parse(event.data) as unknown;
          onMessage(data);
        }
      } catch (cause: unknown) {
        globalThis.reportError(
          cause instanceof Error ? cause : new Error('SSE: failed to parse event data', { cause }),
        );
      }
    },
    onerror(err) {
      if (err instanceof FatalSSEError) throw err;
      return SSE_RECONNECT_DELAY_MS;
    },
  });

  try {
    await cacheEntryRemoved;
  } finally {
    controller.abort();
  }
};
