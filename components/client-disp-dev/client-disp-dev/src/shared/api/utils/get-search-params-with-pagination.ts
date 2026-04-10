import type { PaginationFilter } from '@/shared/api/types';
import { hasValue } from '@/shared/lib/has-value';

/** Максимальное количество элементов по умолчанию. */
const DEFAULT_PAGINATION_LIMIT = 100;

/** Смещение пагинации по умолчанию. */
const DEFAULT_PAGINATION_OFFSET = 0;

/** Номер страницы по умолчанию. */
const DEFAULT_PAGINATION_PAGE = 1;

/** Запрашиваемое количество элементов по умолчанию. */
const DEFAULT_PAGINATION_SIZE = 50;

/**
 * Возвращает {@link URLSearchParams} с пагинацией по умолчанию или пустой {@link URLSearchParams} если параметры пагинации не переданы.
 *
 * @param pagination фильтры пагинации.
 */
export function getSearchParamsWithPagination(pagination?: PaginationFilter) {
  const searchParams = new URLSearchParams();

  if (pagination) {
    if (hasValue(pagination.limit) || hasValue(pagination.offset)) {
      const limit = pagination.limit ?? DEFAULT_PAGINATION_LIMIT;
      const offset = pagination.offset ?? DEFAULT_PAGINATION_OFFSET;
      searchParams.append('limit', limit.toString());
      searchParams.append('offset', offset.toString());
    } else if (hasValue(pagination.page) || hasValue(pagination.size)) {
      const page = pagination.page ?? DEFAULT_PAGINATION_PAGE;
      const size = pagination.size ?? DEFAULT_PAGINATION_SIZE;
      searchParams.append('page', page.toString());
      searchParams.append('size', size.toString());
    }
  }

  return searchParams;
}

/**
 * Возвращает {@link URLSearchParams} со страничной пагинацией.
 *
 * @param pagination фильтры пагинации.
 */
export function getSearchParamsWithPagePagination(pagination: PaginationFilter) {
  const searchParams = new URLSearchParams();

  const page = pagination.page ?? DEFAULT_PAGINATION_PAGE;
  const size = pagination.size ?? DEFAULT_PAGINATION_SIZE;
  searchParams.append('page', page.toString());
  searchParams.append('size', size.toString());

  return searchParams;
}
