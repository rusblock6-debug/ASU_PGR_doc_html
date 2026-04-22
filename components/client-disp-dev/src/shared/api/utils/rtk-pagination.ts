import type { Pagination, PaginationFilter } from '@/shared/api/types';

/**
 * Возвращает делегат `getNextPageParam` для RTK Query infiniteQuery со страничной пагинацией.
 */
function getRTKNextPageParam<T extends Pagination, K extends PaginationFilter>(
  lastPage: T,
  _allPages: readonly T[],
  lastPageParam: K,
) {
  const currentPage = lastPageParam.page ?? 1;
  const hasNextPage = currentPage < lastPage.pages;

  if (!hasNextPage) {
    return undefined;
  }

  return {
    ...lastPageParam,
    page: currentPage + 1,
  };
}

/**
 * Настройки `infiniteQueryOptions` для RTK Query со страничной пагинацией.
 */
export const pageInfiniteQueryOptions = {
  initialPageParam: {},
  getNextPageParam: getRTKNextPageParam,
} as const;
