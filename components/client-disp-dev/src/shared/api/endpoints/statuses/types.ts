import type { Pagination } from '@/shared/api/types/pagination';

/** Представляет модель статуса. */
export interface Status {
  /** Возвращает идентификатор. */
  readonly id: number;
  /** Возвращает отображаемое название статуса. */
  readonly display_name: string;
  /** Возвращает цвет. */
  readonly color: string;
  /** Возвращает аналитическую категорию. */
  readonly analytic_category: string;
  /** Возвращает отображаемое имя аналитической категории. */
  readonly analytic_category_display_name: string;
  /** Возвращает системный статус. */
  readonly system_status: boolean;
  /** Возвращает время создания. */
  readonly created_at: string;
  /** Возвращает время обновления. */
  readonly updated_at: string;
  /** Возвращает системное название статуса (латиница). */
  readonly system_name: string;
  /** Возвращает признак рабочего статуса. */
  readonly is_work_status: boolean;
  /** Возвращает идентификатор организационной категории. */
  readonly organization_category_id?: number | null;
  /** Возвращает название организационной категории. */
  readonly organization_category_name?: string | null;
}

/** Представляет модель данных, получаемую по запросу статусов. */
export interface StatusResponse extends Pagination {
  /** Возвращает список статусов. */
  readonly items: readonly Status[];
}

/** Представляет модель данных для создания статуса. */
export interface CreateStatusRequest {
  /** Возвращает отображаемое название статуса. */
  readonly display_name: string;
  /** Возвращает цвет. */
  readonly color: string;
  /** Возвращает системное название статуса (латиница). */
  readonly system_name?: string | null;
  /** Возвращает аналитическую категорию. */
  readonly analytic_category?: string | null;
  /** Возвращает идентификатор организационной категории. */
  readonly organization_category_id?: number | null;
  /** Возвращает системный статус. */
  readonly system_status?: boolean | null;
  /** Возвращает признак рабочего статуса. */
  readonly is_work_status?: boolean | null;
}

/** Представляет модель данных для редактирования статуса. */
export interface UpdateStatusRequest {
  /** Возвращает отображаемое название статуса. */
  readonly display_name?: string;
  /** Возвращает цвет. */
  readonly color?: string;
  /** Возвращает системное название статуса (латиница). */
  readonly system_name?: string | null;
  /** Возвращает аналитическую категорию. */
  readonly analytic_category?: string;
  /** Возвращает идентификатор организационной категории. */
  readonly organization_category_id?: number | null;
  /** Возвращает системный статус. */
  readonly system_status?: boolean;
  /** Возвращает признак рабочего статуса. */
  readonly is_work_status?: boolean | null;
}
