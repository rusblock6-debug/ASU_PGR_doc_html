import { rtkApi } from '@/shared/api';

import type { MapPlayerPlaybackRequest, MapPlayerPlayback, MapPlayerPlaybackChunkResponse } from './types';

export const mapPlayerRtkApi = rtkApi.injectEndpoints({
  endpoints: (build) => ({
    getMapPlayerPlayback: build.query<MapPlayerPlayback, MapPlayerPlaybackRequest>({
      query: (body) => ({
        url: '/graph/map-player/playback',
        method: 'POST',
        body,
      }),
    }),

    getMapPlayerPlaybackManifest: build.query<MapPlayerPlayback, { readonly hash: string }>({
      query: ({ hash }) => ({
        url: `/graph/map-player/playback/${hash}/manifest`,
        method: 'GET',
      }),
    }),

    getMapPlayerPlaybackChunkByIndex: build.query<
      MapPlayerPlaybackChunkResponse,
      { readonly hash: string; readonly chunkIndex: number }
    >({
      query: ({ hash, chunkIndex }) => ({
        url: `/graph/map-player/playback/${hash}/chunks/${chunkIndex}`,
        method: 'GET',
      }),
    }),
  }),
});

export const {
  useGetMapPlayerPlaybackQuery,
  useLazyGetMapPlayerPlaybackQuery,
  useGetMapPlayerPlaybackManifestQuery,
  useLazyGetMapPlayerPlaybackManifestQuery,
  useGetMapPlayerPlaybackChunkByIndexQuery,
  useLazyGetMapPlayerPlaybackChunkByIndexQuery,
} = mapPlayerRtkApi;
