import { useLogoutMutation } from '@/shared/api/endpoints/auth';
import { authLogout } from '@/shared/lib/auth-actions';
import { useAppDispatch } from '@/shared/lib/hooks/useAppDispatch';
import { tokenStorage } from '@/shared/lib/token-storage';

/**
 * Выход: запрос на бэкенд с `refreshToken` (если есть), затем в `finally` — сброс сессии в Redux (`authLogout`).
 *
 * @returns `logout` — асинхронный обработчик; `isLoading` — состояние RTK Mutation.
 */
export const useLogout = () => {
  const dispatch = useAppDispatch();
  const [logoutMutation, { isLoading }] = useLogoutMutation();

  const logout = async () => {
    const refreshToken = tokenStorage.getRefreshToken();
    try {
      await logoutMutation({ refreshToken }).unwrap();
    } finally {
      dispatch(authLogout());
    }
  };

  return { logout, isLoading };
};
