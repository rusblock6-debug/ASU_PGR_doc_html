import type { LoadTypeCategory } from '@/shared/api/endpoints/load-type-categories';
import type { Pagination } from '@/shared/api/types';

/** Представляет вид груза. */
export interface LoadType {
  /** Идентификатор вида груза. */
  readonly id: number;
  /** Наименование вида груза. */
  readonly name: string;
  /** Плотность вида груза. */
  readonly density: number;
  /** Цвет вида груза. */
  readonly color: string;
  /** Идентификатор категории вида груза. */
  readonly category_id: number;
  /** Категория вида груза. */
  readonly category: LoadTypeCategory;
}

/** Представляет ответ API со списком видов грузов. */
export interface LoadTypesApiResponse extends Pagination {
  readonly items: readonly LoadType[];
}

/** Представляет нормализованные данные видов грузов. */
export interface NormalizedLoadTypes {
  /** Массив ID видов грузов. */
  readonly ids: readonly number[];
  /** Виды грузов по ID для быстрого доступа. */
  readonly entities: Readonly<Record<number, LoadType>>;
}

/** Представляет запрос на создание вида груза. */
export interface CreateLoadTypeRequest {
  /** Наименование вида груза. */
  readonly name: string;
  /** Плотность вида груза. */
  readonly density: number;
  /** Цвет вида груза. */
  readonly color: string;
  /** Идентификатор категории вида груза. */
  readonly category_id: number;
}

/** Представляет параметры обновления вида груза. */
export interface UpdateLoadTypeParams {
  /** Идентификатор вида груза. */
  readonly id: number;
  /** Тело запроса. */
  readonly body: UpdateLoadTypeRequest;
}

/** Представляет запрос на обновление вида груза. */
export interface UpdateLoadTypeRequest {
  /** Наименование вида груза. */
  readonly name: string;
  /** Плотность вида груза. */
  readonly density: number;
  /** Цвет вида груза. */
  readonly color: string;
  /** Идентификатор категории вида груза. */
  readonly category_id: number;
}
