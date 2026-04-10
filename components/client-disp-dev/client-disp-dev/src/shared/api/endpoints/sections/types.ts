import type { Horizon } from '@/shared/api/endpoints/horizons';
import type { Pagination } from '@/shared/api/types';

/** Представляет модель участка. */
export interface Section {
  /** Возвращает идентификатор. */
  readonly id: number;
  /** Возвращает наименование участка. */
  readonly name: string;
  /** Возвращает флаг того, что участок является подрядной организацией. */
  readonly is_contractor_organization: boolean;
  /** Возвращает список горизонтов. */
  readonly horizons: readonly Pick<Horizon, 'id' | 'name'>[];
  /** Возвращает время создания. */
  readonly created_at: string;
  /** Возвращает время обновления. */
  readonly updated_at: string;
}

/** Представляет модель данных, получаемую по запросу участков. */
export interface SectionsResponse extends Pagination {
  readonly items: readonly Section[];
}

/** Представляет модель данных для создания участка. */
export interface CreateSectionRequest {
  /** Возвращает наименование участка. */
  readonly name: string;
  /** Возвращает флаг того, что участок является подрядной организацией. */
  readonly is_contractor_organization: boolean;
  /** Возвращает список идентификаторов горизонтов. */
  readonly horizons: readonly number[];
}

/** Представляет модель данных для редактирования участка. */
export interface UpdateSectionRequest {
  /** Возвращает наименование участка. */
  readonly name?: string;
  /** Возвращает флаг того, что участок является подрядной организацией. */
  readonly is_contractor_organization?: boolean;
  /** Возвращает список идентификаторов горизонтов. */
  readonly horizons?: readonly number[];
}
