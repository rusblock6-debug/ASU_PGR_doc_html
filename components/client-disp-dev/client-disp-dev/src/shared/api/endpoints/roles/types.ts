import type { Pagination } from '@/shared/api/types';

/** Представляет модель данных доступа роли. */
export interface RolePermission {
  /** Возвращает название формы для роли. */
  readonly name: string;
  /** Возвращает признак разрешения для чтения. */
  readonly can_view: boolean;
  /** Возвращает признак разрешения для редактирования. */
  readonly can_edit: boolean;
}

/** Представляет модель роли. */
export interface Role {
  /** Возвращает идентификатор. */
  readonly id: number;
  /** Возвращает наименование. */
  readonly name: string;
  /** Возвращает список наименований разрешений. */
  readonly permissions: readonly RolePermission[];
  /** Возвращает описание. */
  readonly description?: string | null;
}

/** Представляет модель данных, получаемую по запросу ролей. */
export interface RolesResponse extends Pagination {
  /** Возвращает список мест. */
  readonly items: readonly Role[];
}

/** Представляет модель данных для создания роли. */
export interface CreateRoleRequest {
  /** Возвращает наименование. */
  readonly name: string;
  /** Возвращает список наименований разрешений. */
  readonly permissions: readonly RolePermission[];
  /** Возвращает описание. */
  readonly description?: string | null;
}

/** Представляет модель данных для редактирования роли. */
export interface UpdateRoleRequest {
  /** Возвращает наименование. */
  readonly name?: string | null;
  /** Возвращает список наименований разрешений. */
  readonly permissions?: readonly RolePermission[] | null;
  /** Возвращает описание. */
  readonly description?: string | null;
}
