import { useAppSelector } from '@/shared/lib/hooks/useAppSelector';

import { selectIsAuthenticated, selectUser, selectUserPermissions, selectUserRoleName } from '../../model/auth-slice';

/**
 * Хук для получения auth-состояния пользователя из стора.
 */
export const useAuth = () => {
  const isAuthenticated = useAppSelector(selectIsAuthenticated);
  const user = useAppSelector(selectUser);
  const roleName = useAppSelector(selectUserRoleName);
  const permissions = useAppSelector(selectUserPermissions);

  return {
    isAuthenticated,
    user,
    roleName,
    permissions,
  };
};
