import { rtkApi } from '@/shared/api/rtk-api';

import type { TagResponse } from './types';

/**
 * Извлекает отображаемое имя тега из произвольного ответа API (name / title / label / display_name).
 */
function pickTagName(raw: unknown): string {
  if (raw == null || typeof raw !== 'object') {
    return '';
  }
  const o = raw as Record<string, unknown>;
  for (const key of ['name', 'title', 'label', 'display_name'] as const) {
    const v = o[key];
    if (typeof v === 'string' && v.trim()) {
      return v.trim();
    }
  }
  return '';
}

const tagsApi = rtkApi.injectEndpoints({
  endpoints: (builder) => ({
    getTagById: builder.query<TagResponse, string>({
      query: (tagId) => `/api/tags/${encodeURIComponent(tagId)}`,
      extraOptions: { backend: 'graph' as const },
      transformResponse: (raw: unknown) => {
        const name = pickTagName(raw);
        if (raw != null && typeof raw === 'object') {
          return { ...(raw as Record<string, unknown>), name } as TagResponse;
        }
        return { name };
      },
      providesTags: (_result, _error, id) => [{ type: 'Tag' as const, id }],
    }),
  }),
});

export const { useGetTagByIdQuery } = tagsApi;
