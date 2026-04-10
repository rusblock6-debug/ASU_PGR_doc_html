import { type JSX, useMemo } from 'react';
import { Navigate, useLocation } from 'react-router-dom';

import { UserRole, type UserRoleType } from '@/entities/user';

import { getRouteForbidden, getRouteMain } from '@/shared/routes/router';

interface RequireAuthProps {
  readonly children: JSX.Element;
  readonly roles?: UserRoleType[];
}

// Mock данные
const mockUser = {
  id: '1',
  username: 'manager_user',
  roles: [UserRole.MANAGER] as UserRoleType[],
};

export function RequireAuth({ children, roles }: RequireAuthProps) {
  const location = useLocation();
  // Временное решение, пока не реализован функционал авторизации.
  // пока отключил авторизацию для демо
  // const userLogin = localStorage.getItem('USER_LOGIN');
  //userLogin && userLogin.length > 0;
  const auth = true;

  const userRoles = mockUser.roles;

  const hasRequiredRoles = useMemo(() => {
    if (!roles) {
      return true;
    }

    return roles.some((requiredRole) => {
      const hasRole = userRoles?.includes(requiredRole);
      return hasRole;
    });
  }, [roles, userRoles]);

  if (!auth) {
    return (
      <Navigate
        to={getRouteMain()}
        state={{ from: location }}
        replace
      />
    );
  }

  if (!hasRequiredRoles) {
    return (
      <Navigate
        to={getRouteForbidden()}
        state={{ from: location }}
        replace
      />
    );
  }

  return children;
}
