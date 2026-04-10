import type { Pagination } from '@/shared/api/types/pagination';

/** Представляет модель организационной категории. */
export interface OrganizationCategory {
  /** Возвращает идентификатор. */
  readonly id: number;
  /** Возвращает наименование организационной категории. */
  readonly name: string;
  /** Возвращает время создания. */
  readonly created_at: string;
  /** Возвращает время обновления. */
  readonly updated_at: string;
}

/** Представляет модель данных, получаемую по запросу организационных категорий. */
export interface OrganizationCategoryResponse extends Pagination {
  /** Возвращает список организационных категорий. */
  readonly items: readonly OrganizationCategory[];
}

/** Представляет модель данных для создания организационной категории. */
export interface CreateOrganizationCategoryRequest {
  /** Возвращает наименование организационной категории. */
  readonly name: string;
}

/** Представляет модель данных для редактирования организационной категории. */
export interface UpdateOrganizationCategoryRequest {
  /** Возвращает наименование организационной категории. */
  readonly name?: string;
}
