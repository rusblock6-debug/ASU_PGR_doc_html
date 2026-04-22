import { Navigate, Outlet } from 'react-router-dom';

import { useAuth } from '@/shared/lib/auth';
import { getRouteLogin } from '@/shared/routes/router';

/** Редирект на /login, если мок-сессия не установлена. */
export function AuthGuard() {
  const { isAuthenticated } = useAuth();

  if (!isAuthenticated) {
    return (
      <Navigate
        to={getRouteLogin()}
        replace
      />
    );
  }

  return <Outlet />;
}
