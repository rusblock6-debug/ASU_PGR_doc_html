import { rtkApi } from '@/shared/api';
import { createAuthenticatedSSE } from '@/shared/api/utils';

import type { StreamAllMessage } from './types';

/**
 * Проверяет, что значение соответствует одному из сообщений SSE-потока `/trip/events/stream/all`.
 */
const isStreamAllMessage = (value: unknown): value is StreamAllMessage => {
  if (typeof value !== 'object' || value === null) return false;

  const message = value as Record<string, unknown>;

  if (message.event_type === 'state_transition') return true;
  if (message.event_type === 'history_changed') {
    return (
      typeof message.vehicle_id === 'number' &&
      typeof message.shift_date === 'string' &&
      typeof message.shift_num === 'number'
    );
  }

  return false;
};

export const streamsRtkApi = rtkApi.injectEndpoints({
  endpoints: (build) => ({
    getStreamAll: build.query<StreamAllMessage | undefined, void>({
      queryFn: () => ({ data: undefined }),
      keepUnusedDataFor: 0,
      async onCacheEntryAdded(_, { updateCachedData, cacheDataLoaded, cacheEntryRemoved, dispatch }) {
        await createAuthenticatedSSE({
          url: '/trip/events/stream/all',
          dispatch,
          cacheDataLoaded,
          cacheEntryRemoved,
          onMessage(data) {
            if (!isStreamAllMessage(data)) return;
            updateCachedData(() => data);
          },
        });
      },
    }),
  }),
});

export const { useGetStreamAllQuery } = streamsRtkApi;
