import { rtkApi } from '@/shared/api/rtk-api';

import type { OrganizationCategoryResponse } from './types';

/** Нормализует payload `/api/organization-categories` к массиву категорий. */
function normalizeOrganizationCategoriesPayload(raw: unknown): OrganizationCategoryResponse[] {
  if (Array.isArray(raw)) {
    return raw as OrganizationCategoryResponse[];
  }

  if (!raw || typeof raw !== 'object') {
    return [];
  }

  const payload = raw as Record<string, unknown>;
  const list = payload.items ?? payload.data ?? payload.results ?? payload.organization_categories;

  if (!Array.isArray(list)) {
    return [];
  }

  return list as OrganizationCategoryResponse[];
}

export const organizationCategoriesApi = rtkApi.injectEndpoints({
  endpoints: (builder) => ({
    getOrganizationCategories: builder.query<OrganizationCategoryResponse[], void>({
      query: () => '/api/organization-categories',
      extraOptions: { backend: 'enterprise' as const },
      transformResponse: (raw: unknown) => normalizeOrganizationCategoriesPayload(raw),
    }),
  }),
});

export const { useGetOrganizationCategoriesQuery } = organizationCategoriesApi;
