import { rtkApi } from '@/shared/api';

import type { StreamAllMessage } from './types';

export const streamsRtkApi = rtkApi.injectEndpoints({
  endpoints: (build) => ({
    getStreamAll: build.query<StreamAllMessage | undefined, void>({
      queryFn: () => ({ data: undefined }),
      keepUnusedDataFor: 0,
      async onCacheEntryAdded(_, { updateCachedData, cacheDataLoaded, cacheEntryRemoved }) {
        const eventSource = new EventSource(`/api/events/stream/all`);

        const listener = (event: MessageEvent) => {
          const data = JSON.parse(event.data as string) as StreamAllMessage;
          updateCachedData(() => data);
        };

        eventSource.addEventListener('message', listener);

        try {
          await cacheDataLoaded;
        } catch {
          // Временное решение. Нужно сделать механизм для повторной попытки соединения при возникновении ошибки.
          console.error('Stream error');
        }

        await cacheEntryRemoved;
        eventSource.close();
      },
    }),
  }),
});

export const { useGetStreamAllQuery } = streamsRtkApi;
