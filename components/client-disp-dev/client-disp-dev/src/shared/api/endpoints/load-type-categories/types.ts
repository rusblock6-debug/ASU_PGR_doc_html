import type { Pagination } from '@/shared/api/types';

/** Представляет категорию вида груза. */
export interface LoadTypeCategory {
  /** ID категории. */
  readonly id: number;
  /** Наименование категории вида груза. */
  readonly name: string;
  /** Является ли данная категория полезным ископаемым. */
  readonly is_mineral: boolean;
}

/** Представляет ответ API со списком категорий видов грузов. */
export interface LoadTypeCategoriesApiResponse extends Pagination {
  readonly items: readonly LoadTypeCategory[];
}

/** Представляет запрос на создание категории вида груза. */
export interface CreateLoadTypeCategoryRequest {
  /** Наименование категории вида груза. */
  readonly name: string;
  /** Является ли данная категория полезным ископаемым. */
  readonly is_mineral?: boolean;
}

/** Представляет запрос на обновление категории вида груза. */
export interface UpdateLoadTypeCategoryRequest {
  /** Наименование категории вида груза. */
  readonly name: string;
  /** Является ли данная категория полезным ископаемым. */
  readonly is_mineral?: boolean;
}

/** Представляет параметры обновления категории вида груза. */
export interface UpdateLoadTypeCategoryParams {
  /** ID категории. */
  readonly id: number;
  /** Тело запроса. */
  readonly body: UpdateLoadTypeCategoryRequest;
}
