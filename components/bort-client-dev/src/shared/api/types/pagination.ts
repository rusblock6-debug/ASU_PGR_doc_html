/**
 * Представляет модель пагинации.
 */
export interface Pagination {
  /**
   * Возвращает общее количество элементов списка.
   */
  readonly total: number;
  /**
   * Возвращает текущую страницу.
   */
  readonly page: number;
  /**
   * Возвращает количество элементов на странице.
   */
  readonly size: number;
  /**
   * Возвращает общее количество страниц.
   */
  readonly pages: number;
}

/**
 * Представляет модель параметров фильтрации для пагинации.
 */
export interface PaginationFilter {
  /**
   * Возвращает максимальное количество элементов для возврата.
   */
  readonly limit?: number;
  /**
   * Возвращает смещение пагинации.
   */
  readonly offset?: number;
  /**
   * Возвращает номер страницы.
   */
  readonly page?: number;
  /**
   * Возвращает количество элементов.
   */
  readonly size?: number;
}
