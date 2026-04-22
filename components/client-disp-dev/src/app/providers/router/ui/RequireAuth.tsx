import type { PropsWithChildren } from 'react';
import { Navigate, useLocation } from 'react-router-dom';

import { selectIsAuthenticated, selectUserPermissions } from '@/entities/user';

import { hasValue } from '@/shared/lib/has-value';
import { useAppSelector } from '@/shared/lib/hooks/useAppSelector';
import { getRouteForbidden, getRouteMain } from '@/shared/routes/router';

/** Пропсы {@link RequireAuth}. */
interface RequireAuthProps {
  /** Имя разрешения из RolePermission.name. Если задано — доступ разрешён только при can_view === true. */
  readonly permission?: string;
}

/**
 * Гард роутов: проверяет авторизацию и (опционально) доступ по permission.can_view.
 */
export function RequireAuth({ children, permission }: PropsWithChildren<RequireAuthProps>) {
  const location = useLocation();
  const isAuthenticated = useAppSelector(selectIsAuthenticated);
  const permissions = useAppSelector(selectUserPermissions);

  const hasAccess = !hasValue(permission) || permissions.some((p) => p.name === permission && p.can_view);

  if (!isAuthenticated) {
    return (
      <Navigate
        to={getRouteMain()}
        state={{ from: location }}
        replace
      />
    );
  }

  if (!hasAccess) {
    return (
      <Navigate
        to={getRouteForbidden()}
        state={{ from: location }}
        replace
      />
    );
  }

  return <>{children}</>;
}
