import type { RolePermission } from '@/shared/api/endpoints/roles/types';

/**
 * Разрешение, приходящее в JWT payload (как permission роли).
 */
export type JwtPermission = RolePermission & {
  /** Идентификатор разрешения. */
  readonly id: number;
};

/**
 * Роль пользователя в JWT payload.
 */
export interface JwtUserRole {
  /** Идентификатор роли. */
  readonly id: number;
  /** Наименование роли. */
  readonly name: string;
  /** Список разрешений роли. */
  readonly permissions: readonly JwtPermission[];
}

/**
 * JWT payload пользователя.
 */
export interface JwtPayload {
  /** Идентификатор пользователя. */
  readonly id: number;
  /** Логин пользователя. */
  readonly username: string;
  /** Роль пользователя. */
  readonly role: JwtUserRole;
  /** Время истечения токена в секундах (Unix time). */
  readonly exp: number;
}
