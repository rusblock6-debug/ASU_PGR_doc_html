import { rtkApi } from '@/shared/api/rtk-api';

import type { StatusResponse } from './types';

/** Нормализует payload `/api/statuses` к массиву статусов. */
function normalizeStatusesPayload(raw: unknown): StatusResponse[] {
  if (Array.isArray(raw)) {
    return raw as StatusResponse[];
  }

  if (!raw || typeof raw !== 'object') {
    return [];
  }

  const payload = raw as Record<string, unknown>;
  const list = payload.items ?? payload.data ?? payload.results ?? payload.statuses;

  if (!Array.isArray(list)) {
    return [];
  }

  return list as StatusResponse[];
}

export const statusesApi = rtkApi.injectEndpoints({
  endpoints: (builder) => ({
    getStatuses: builder.query<StatusResponse[], void>({
      query: () => '/api/statuses',
      extraOptions: { backend: 'enterprise' as const },
      transformResponse: (raw: unknown) => normalizeStatusesPayload(raw),
    }),
  }),
});

export const { useGetStatusesQuery } = statusesApi;
