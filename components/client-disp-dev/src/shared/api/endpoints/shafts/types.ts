import type { Pagination } from '@/shared/api/types/pagination';

/** Представляет модель шахты. */
export interface Shaft {
  /** Возвращает идентификатор. */
  readonly id: number;
  /** Возвращает наименование организационной категории. */
  readonly name: string;
  /** Возвращает время создания. */
  readonly created_at: string;
  /** Возвращает время обновления. */
  readonly updated_at: string;
}

/** Представляет модель данных, получаемую по запросу шахт. */
export interface ShaftsResponse extends Pagination {
  /** Возвращает список шахт. */
  readonly items: readonly Shaft[];
}

/** Представляет модель данных для создания шахты. */
export interface CreateShaftsRequest {
  /** Возвращает наименование шахты. */
  readonly name?: string;
}

/** Представляет модель данных для редактирования шахты. */
export interface UpdateShaftRequest {
  /** Возвращает наименование шахты. */
  readonly name?: string;
}
