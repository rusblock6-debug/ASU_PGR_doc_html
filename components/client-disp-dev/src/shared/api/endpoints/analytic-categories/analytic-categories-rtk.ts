import { rtkApi } from '@/shared/api';

import type { AnalyticCategoryResponse } from './types';

/**
 * Запросы для аналитических категорий.
 */
export const analyticCategoriesRtkApi = rtkApi.injectEndpoints({
  endpoints: (builder) => ({
    getAllAnalyticCategories: builder.query<AnalyticCategoryResponse, void>({
      query: () => {
        return '/enterprise/statuses/analytic-categories';
      },

      providesTags: ['Analytic-categories'],
    }),
  }),
});

export const { useGetAllAnalyticCategoriesQuery } = analyticCategoriesRtkApi;
