import type { AppRouteType } from './router';
import { AppRoutes } from './router';

/** Публичные роуты — доступны всем без проверки permission. */
const PUBLIC_ROUTES = [
  AppRoutes.MAIN,
  AppRoutes.APP,
  AppRoutes.WORKSPACE,
  AppRoutes.FORBIDDEN,
  AppRoutes.NOT_FOUND,
] as const;

const publicRoutes = new Set<AppRouteType>(PUBLIC_ROUTES);

/** Роуты с кастомным доступом (не по конвенции key = permission). */
const PERMISSION_OVERRIDES: Partial<Record<AppRouteType, AppRouteType>> = {
  [AppRoutes.DISPATCH_MAP]: AppRoutes.MAP,
} as const;

/**
 * Возвращает имя permission для роута.
 * - Публичный роут → undefined
 * - Есть override → кастомный доступ
 * - Иначе → ключ роута (конвенция по умолчанию)
 */
export function getRoutePermission(key: AppRouteType) {
  if (publicRoutes.has(key)) return undefined;
  return PERMISSION_OVERRIDES[key] ?? key;
}
